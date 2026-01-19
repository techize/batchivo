"""Square webhook processing service with robust handling.

Features:
- Idempotency tracking (prevent duplicate processing)
- Database transactions for state changes
- Retry logic with exponential backoff
- Dead-letter queue for permanently failed events
- Comprehensive logging for debugging
"""

import base64
import hashlib
import hmac
import logging
import traceback
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.payment_log import PaymentLog, PaymentLogOperation, PaymentLogStatus
from app.models.webhook_event import (
    WebhookDeadLetter,
    WebhookEvent,
    WebhookEventSource,
    WebhookEventStatus,
)

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRY_ATTEMPTS = 5
RETRY_BACKOFF_BASE = 60  # Base delay in seconds
RETRY_BACKOFF_MULTIPLIER = 2  # Exponential multiplier


class SquareWebhookService:
    """Service for processing Square webhook events with robustness features."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def verify_signature(
        self,
        body: bytes,
        signature: str,
        webhook_key: str,
        notification_url: str,
    ) -> bool:
        """
        Verify Square webhook signature.

        Square uses HMAC-SHA256 with URL + body as the message.
        https://developer.squareup.com/docs/webhooks/validate-notifications

        Args:
            body: Raw request body bytes
            signature: x-square-hmacsha256-signature header value
            webhook_key: Square webhook signature key from settings
            notification_url: Full URL of the webhook endpoint

        Returns:
            True if signature is valid, False otherwise
        """
        if not webhook_key:
            logger.warning("Webhook signature key not configured, skipping validation")
            return True

        if not signature:
            logger.warning("Missing webhook signature header")
            return False

        string_to_sign = notification_url + body.decode("utf-8")
        expected_signature = hmac.new(
            webhook_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_signature_b64 = base64.b64encode(expected_signature).decode("utf-8")

        is_valid = hmac.compare_digest(signature, expected_signature_b64)
        if not is_valid:
            logger.warning("Invalid Square webhook signature")

        return is_valid

    async def process_webhook(
        self,
        event_data: dict,
        signature_valid: bool = True,
    ) -> dict:
        """
        Process a Square webhook event with idempotency and transaction safety.

        Args:
            event_data: Parsed webhook JSON payload
            signature_valid: Whether signature validation passed

        Returns:
            dict with processing status and details
        """
        event_type = event_data.get("type", "unknown")
        event_id = event_data.get("event_id") or self._generate_event_id(event_data)

        logger.info(f"Processing Square webhook: type={event_type} event_id={event_id}")

        # Check for duplicate (idempotency)
        existing_event = await self._get_existing_event(event_id)
        if existing_event:
            if existing_event.status == WebhookEventStatus.COMPLETED.value:
                logger.info(f"Event {event_id} already processed successfully, skipping")
                return {
                    "status": "duplicate",
                    "message": "Event already processed",
                    "event_id": event_id,
                }
            elif existing_event.status == WebhookEventStatus.PROCESSING.value:
                logger.warning(f"Event {event_id} is currently being processed")
                return {
                    "status": "processing",
                    "message": "Event is currently being processed",
                    "event_id": event_id,
                }

        # Create or get webhook event record
        webhook_event = await self._create_or_update_event(
            event_id=event_id,
            event_type=event_type,
            payload=event_data,
            signature_valid=signature_valid,
        )

        # Process the event
        try:
            result = await self._process_event(webhook_event, event_data)

            # Mark as completed
            await self._mark_completed(webhook_event, result)

            return {
                "status": "processed",
                "message": "Event processed successfully",
                "event_id": event_id,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Error processing webhook {event_id}: {e}")
            logger.debug(traceback.format_exc())

            # Handle failure with retry logic
            await self._handle_failure(webhook_event, str(e), traceback.format_exc())

            return {
                "status": "failed",
                "message": f"Processing failed: {str(e)}",
                "event_id": event_id,
                "will_retry": webhook_event.attempt_count < webhook_event.max_attempts,
            }

    async def _get_existing_event(self, event_id: str) -> Optional[WebhookEvent]:
        """Check if event has already been received."""
        result = await self.db.execute(
            select(WebhookEvent).where(
                WebhookEvent.event_id == event_id,
                WebhookEvent.source == WebhookEventSource.SQUARE.value,
            )
        )
        return result.scalar_one_or_none()

    async def _create_or_update_event(
        self,
        event_id: str,
        event_type: str,
        payload: dict,
        signature_valid: bool,
    ) -> WebhookEvent:
        """Create a new event record or update existing for retry."""
        now = datetime.now(timezone.utc)

        # Extract payment/refund IDs from payload
        payment_id = None
        refund_id = None
        event_object = payload.get("data", {}).get("object", {})

        if "payment" in event_object:
            payment_id = event_object["payment"].get("id")
        if "refund" in event_object:
            refund_id = event_object["refund"].get("id")
            payment_id = payment_id or event_object["refund"].get("payment_id")

        # Try to get existing event
        existing = await self._get_existing_event(event_id)

        if existing:
            # Update for retry
            existing.status = WebhookEventStatus.PROCESSING.value
            existing.attempt_count += 1
            existing.last_processed_at = now
            await self.db.commit()
            return existing

        # Create new event
        webhook_event = WebhookEvent(
            event_id=event_id,
            source=WebhookEventSource.SQUARE.value,
            event_type=event_type,
            status=WebhookEventStatus.PROCESSING.value,
            payload=payload,
            payment_id=payment_id,
            refund_id=refund_id,
            attempt_count=1,
            first_received_at=now,
            last_processed_at=now,
            signature_valid=signature_valid,
        )

        self.db.add(webhook_event)
        await self.db.commit()
        await self.db.refresh(webhook_event)

        return webhook_event

    async def _process_event(
        self,
        webhook_event: WebhookEvent,
        event_data: dict,
    ) -> dict:
        """Process event based on type with database transactions."""
        event_type = event_data.get("type", "")
        event_object = event_data.get("data", {}).get("object", {})

        result = {"event_type": event_type, "actions": []}

        # Route to appropriate handler
        if event_type == "payment.created":
            await self._handle_payment_created(event_object, webhook_event, result)
        elif event_type == "payment.updated":
            await self._handle_payment_updated(event_object, webhook_event, result)
        elif event_type == "payment.failed":
            await self._handle_payment_failed(event_object, webhook_event, result)
        elif event_type == "refund.created":
            await self._handle_refund_created(event_object, webhook_event, result)
        elif event_type == "refund.updated":
            await self._handle_refund_updated(event_object, webhook_event, result)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
            result["actions"].append(f"Logged unhandled event: {event_type}")

        return result

    async def _handle_payment_created(
        self,
        event_object: dict,
        webhook_event: WebhookEvent,
        result: dict,
    ) -> None:
        """Handle payment.created webhook event."""
        payment = event_object.get("payment", {})
        payment_id = payment.get("id")
        status = payment.get("status")
        amount = payment.get("amount_money", {}).get("amount", 0)
        currency = payment.get("amount_money", {}).get("currency", "GBP")

        logger.info(
            f"Payment created: payment_id={payment_id} status={status} "
            f"amount={amount} {currency}"
        )

        # Log the payment event
        await self._create_payment_log(
            payment_id=payment_id,
            operation=PaymentLogOperation.WEBHOOK,
            status=PaymentLogStatus.SUCCESS,
            amount=amount,
            currency=currency,
            request_data={"event_type": "payment.created", "status": status},
            response_data=payment,
        )

        result["actions"].append(f"Logged payment.created: {payment_id}")

    async def _handle_payment_updated(
        self,
        event_object: dict,
        webhook_event: WebhookEvent,
        result: dict,
    ) -> None:
        """Handle payment.updated webhook event with transaction safety."""
        payment = event_object.get("payment", {})
        payment_id = payment.get("id")
        new_status = payment.get("status")

        logger.info(f"Payment updated: payment_id={payment_id} status={new_status}")

        # Find associated order
        order_result = await self.db.execute(
            select(Order).where(Order.payment_id == payment_id)
        )
        order = order_result.scalar_one_or_none()

        if order:
            # Update order within transaction
            old_status = order.payment_status
            order.payment_status = new_status
            order.updated_at = datetime.now(timezone.utc)

            # Link order to webhook event
            webhook_event.order_id = order.id

            await self.db.commit()

            logger.info(
                f"Updated order {order.order_number} payment_status: "
                f"{old_status} -> {new_status}"
            )
            result["actions"].append(
                f"Updated order {order.order_number} payment status to {new_status}"
            )
        else:
            logger.warning(f"No order found for payment_id={payment_id}")
            result["actions"].append(f"No order found for payment_id={payment_id}")

        # Log the event
        await self._create_payment_log(
            payment_id=payment_id,
            order_id=order.id if order else None,
            order_number=order.order_number if order else None,
            operation=PaymentLogOperation.WEBHOOK,
            status=PaymentLogStatus.SUCCESS,
            request_data={"event_type": "payment.updated", "new_status": new_status},
        )

    async def _handle_payment_failed(
        self,
        event_object: dict,
        webhook_event: WebhookEvent,
        result: dict,
    ) -> None:
        """Handle payment.failed webhook event with comprehensive error logging."""
        payment = event_object.get("payment", {})
        payment_id = payment.get("id")
        status = payment.get("status")
        amount = payment.get("amount_money", {}).get("amount", 0)
        currency = payment.get("amount_money", {}).get("currency", "GBP")

        # Extract error details from payment
        errors = payment.get("processing_fee", {})  # Square sometimes puts errors here
        card_details = payment.get("card_details", {})
        error_code = card_details.get("errors", [{}])[0].get("code") if card_details.get(
            "errors"
        ) else None
        error_detail = card_details.get("errors", [{}])[0].get("detail") if card_details.get(
            "errors"
        ) else None

        # Also check top-level errors
        if not error_code and payment.get("errors"):
            error_code = payment["errors"][0].get("code")
            error_detail = payment["errors"][0].get("detail")

        logger.error(
            f"Payment FAILED: payment_id={payment_id} status={status} "
            f"error_code={error_code} error_detail={error_detail}"
        )

        # Find associated order if any
        order_result = await self.db.execute(
            select(Order).where(Order.payment_id == payment_id)
        )
        order = order_result.scalar_one_or_none()

        if order:
            # Update order with failed status
            order.payment_status = "FAILED"
            order.updated_at = datetime.now(timezone.utc)
            webhook_event.order_id = order.id
            await self.db.commit()

            result["actions"].append(
                f"Updated order {order.order_number} payment status to FAILED"
            )

        # Create detailed payment log for failed payment
        await self._create_payment_log(
            payment_id=payment_id,
            order_id=order.id if order else None,
            order_number=order.order_number if order else None,
            operation=PaymentLogOperation.WEBHOOK,
            status=PaymentLogStatus.FAILED,
            amount=amount,
            currency=currency,
            error_code=error_code,
            error_message=error_detail,
            request_data={
                "event_type": "payment.failed",
                "payment_status": status,
            },
            response_data={
                "payment": payment,
                "card_details": card_details,
                "errors": payment.get("errors", []),
            },
        )

        result["actions"].append(f"Logged payment failure: {payment_id}")
        result["error_code"] = error_code
        result["error_detail"] = error_detail

    async def _handle_refund_created(
        self,
        event_object: dict,
        webhook_event: WebhookEvent,
        result: dict,
    ) -> None:
        """Handle refund.created webhook event."""
        refund = event_object.get("refund", {})
        refund_id = refund.get("id")
        payment_id = refund.get("payment_id")
        status = refund.get("status")
        amount = refund.get("amount_money", {}).get("amount", 0)
        currency = refund.get("amount_money", {}).get("currency", "GBP")
        reason = refund.get("reason")

        logger.info(
            f"Refund created: refund_id={refund_id} payment_id={payment_id} "
            f"status={status} amount={amount} {currency}"
        )

        # Find associated order
        order_result = await self.db.execute(
            select(Order).where(Order.payment_id == payment_id)
        )
        order = order_result.scalar_one_or_none()

        if order and status == "COMPLETED":
            # Refund is already complete - update order status
            order.status = OrderStatus.REFUNDED
            order.payment_status = "REFUNDED"
            order.updated_at = datetime.now(timezone.utc)
            webhook_event.order_id = order.id
            await self.db.commit()

            logger.info(f"Updated order {order.order_number} to REFUNDED status")
            result["actions"].append(
                f"Updated order {order.order_number} to REFUNDED status"
            )
        elif order and status == "PENDING":
            # Refund is pending - log but don't update order yet
            webhook_event.order_id = order.id
            await self.db.commit()

            logger.info(f"Refund pending for order {order.order_number}")
            result["actions"].append(f"Refund pending for order {order.order_number}")
        elif not order:
            logger.warning(f"No order found for payment_id={payment_id}")
            result["actions"].append(f"No order found for payment_id={payment_id}")

        # Log the refund event
        await self._create_payment_log(
            payment_id=payment_id,
            refund_id=refund_id,
            order_id=order.id if order else None,
            order_number=order.order_number if order else None,
            operation=PaymentLogOperation.REFUND,
            status=PaymentLogStatus.SUCCESS if status == "COMPLETED" else PaymentLogStatus.INITIATED,
            amount=amount,
            currency=currency,
            request_data={
                "event_type": "refund.created",
                "refund_status": status,
                "reason": reason,
            },
            response_data=refund,
        )

    async def _handle_refund_updated(
        self,
        event_object: dict,
        webhook_event: WebhookEvent,
        result: dict,
    ) -> None:
        """Handle refund.updated webhook event."""
        refund = event_object.get("refund", {})
        refund_id = refund.get("id")
        payment_id = refund.get("payment_id")
        status = refund.get("status")
        amount = refund.get("amount_money", {}).get("amount", 0)

        logger.info(f"Refund updated: refund_id={refund_id} status={status}")

        if status == "COMPLETED":
            # Find and update order
            order_result = await self.db.execute(
                select(Order).where(Order.payment_id == payment_id)
            )
            order = order_result.scalar_one_or_none()

            if order:
                order.status = OrderStatus.REFUNDED
                order.payment_status = "REFUNDED"
                order.updated_at = datetime.now(timezone.utc)
                webhook_event.order_id = order.id
                await self.db.commit()

                logger.info(f"Updated order {order.order_number} to REFUNDED status")
                result["actions"].append(
                    f"Updated order {order.order_number} to REFUNDED status"
                )

            # Log the successful refund
            await self._create_payment_log(
                payment_id=payment_id,
                refund_id=refund_id,
                order_id=order.id if order else None,
                order_number=order.order_number if order else None,
                operation=PaymentLogOperation.REFUND,
                status=PaymentLogStatus.SUCCESS,
                amount=amount,
                request_data={"event_type": "refund.updated", "refund_status": status},
            )
        elif status == "FAILED":
            # Log failed refund
            logger.error(f"Refund FAILED: refund_id={refund_id}")

            await self._create_payment_log(
                payment_id=payment_id,
                refund_id=refund_id,
                operation=PaymentLogOperation.REFUND,
                status=PaymentLogStatus.FAILED,
                amount=amount,
                error_code="REFUND_FAILED",
                error_message=f"Refund {refund_id} failed",
                request_data={"event_type": "refund.updated", "refund_status": status},
                response_data=refund,
            )
            result["actions"].append(f"Logged failed refund: {refund_id}")

    async def _mark_completed(
        self,
        webhook_event: WebhookEvent,
        result: dict,
    ) -> None:
        """Mark webhook event as successfully completed."""
        now = datetime.now(timezone.utc)
        webhook_event.status = WebhookEventStatus.COMPLETED.value
        webhook_event.completed_at = now
        webhook_event.processing_result = result
        webhook_event.error_message = None
        webhook_event.error_details = None

        await self.db.commit()
        logger.info(f"Webhook event {webhook_event.event_id} completed successfully")

    async def _handle_failure(
        self,
        webhook_event: WebhookEvent,
        error_message: str,
        error_traceback: str,
    ) -> None:
        """Handle webhook processing failure with retry logic."""
        now = datetime.now(timezone.utc)
        webhook_event.error_message = error_message
        webhook_event.error_details = {
            "traceback": error_traceback,
            "attempt": webhook_event.attempt_count,
            "timestamp": now.isoformat(),
        }

        if webhook_event.attempt_count < webhook_event.max_attempts:
            # Schedule retry with exponential backoff
            delay = RETRY_BACKOFF_BASE * (RETRY_BACKOFF_MULTIPLIER ** (webhook_event.attempt_count - 1))
            webhook_event.status = WebhookEventStatus.FAILED.value
            webhook_event.next_retry_at = now + timedelta(seconds=delay)

            logger.warning(
                f"Webhook {webhook_event.event_id} failed (attempt {webhook_event.attempt_count}), "
                f"will retry in {delay}s"
            )
        else:
            # Max retries exceeded - move to dead letter queue
            webhook_event.status = WebhookEventStatus.DEAD_LETTER.value
            await self._create_dead_letter(webhook_event, error_message)

            logger.error(
                f"Webhook {webhook_event.event_id} moved to dead letter queue "
                f"after {webhook_event.attempt_count} attempts"
            )

        await self.db.commit()

    async def _create_dead_letter(
        self,
        webhook_event: WebhookEvent,
        failure_reason: str,
    ) -> None:
        """Create dead letter record for permanently failed event."""
        now = datetime.now(timezone.utc)

        dead_letter = WebhookDeadLetter(
            webhook_event_id=webhook_event.id,
            source=webhook_event.source,
            event_id=webhook_event.event_id,
            event_type=webhook_event.event_type,
            failure_reason=failure_reason,
            total_attempts=webhook_event.attempt_count,
            first_failure_at=webhook_event.first_received_at,
            last_failure_at=now,
            error_history=[
                {
                    "attempt": webhook_event.attempt_count,
                    "error": failure_reason,
                    "details": webhook_event.error_details,
                    "timestamp": now.isoformat(),
                }
            ],
        )

        self.db.add(dead_letter)
        logger.warning(f"Created dead letter for webhook {webhook_event.event_id}")

    async def _create_payment_log(
        self,
        payment_id: Optional[str] = None,
        refund_id: Optional[str] = None,
        order_id: Optional[UUID] = None,
        order_number: Optional[str] = None,
        operation: str = PaymentLogOperation.WEBHOOK,
        status: str = PaymentLogStatus.SUCCESS,
        amount: Optional[int] = None,
        currency: Optional[str] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        request_data: Optional[dict] = None,
        response_data: Optional[dict] = None,
    ) -> None:
        """Create a payment log entry for auditing."""
        now = datetime.now(timezone.utc)

        log = PaymentLog(
            payment_id=payment_id,
            refund_id=refund_id,
            order_id=order_id,
            order_number=order_number,
            operation=operation,
            status=status,
            amount=amount,
            currency=currency or "GBP",
            error_code=error_code,
            error_message=error_message,
            request_data=request_data,
            response_data=response_data,
            started_at=now,
            completed_at=now,
        )

        self.db.add(log)
        # Don't commit here - let the caller manage the transaction

    def _generate_event_id(self, event_data: dict) -> str:
        """Generate a unique event ID if not provided by Square."""
        import hashlib
        import json

        # Create a hash of the event data as fallback
        event_str = json.dumps(event_data, sort_keys=True)
        return f"generated-{hashlib.sha256(event_str.encode()).hexdigest()[:32]}"


async def retry_failed_webhooks(db: AsyncSession, max_events: int = 10) -> int:
    """
    Process failed webhook events that are due for retry.

    This should be called periodically by a background task or cron job.

    Args:
        db: Database session
        max_events: Maximum number of events to process in one batch

    Returns:
        Number of events processed
    """
    now = datetime.now(timezone.utc)

    # Find events due for retry
    result = await db.execute(
        select(WebhookEvent)
        .where(
            WebhookEvent.status == WebhookEventStatus.FAILED.value,
            WebhookEvent.next_retry_at <= now,
            WebhookEvent.attempt_count < WebhookEvent.max_attempts,
        )
        .order_by(WebhookEvent.next_retry_at)
        .limit(max_events)
    )
    events = list(result.scalars().all())

    if not events:
        return 0

    logger.info(f"Found {len(events)} webhook events to retry")

    service = SquareWebhookService(db)
    processed = 0

    for event in events:
        try:
            await service.process_webhook(
                event_data=event.payload,
                signature_valid=event.signature_valid or False,
            )
            processed += 1
        except Exception as e:
            logger.error(f"Error retrying webhook {event.event_id}: {e}")

    return processed
