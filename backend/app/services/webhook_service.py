"""Webhook delivery service for outbound event notifications.

Handles:
- Sending webhooks to subscriber URLs
- HMAC signature generation
- Retry logic with exponential backoff
- Auto-disabling failed subscriptions
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import (
    DeliveryStatus,
    WebhookDelivery,
    WebhookEventType,
    WebhookSubscription,
)

logger = logging.getLogger(__name__)

# Configuration
MAX_RETRY_ATTEMPTS = 3
FAILURE_DISABLE_THRESHOLD = 10
DELIVERY_TIMEOUT_SECONDS = 30
MAX_RESPONSE_BODY_LENGTH = 2000

# Exponential backoff intervals (seconds)
RETRY_INTERVALS = [60, 300, 900]  # 1 min, 5 min, 15 min


class WebhookService:
    """Service for managing and delivering webhooks."""

    def __init__(self, db: AsyncSession):
        """Initialize webhook service.

        Args:
            db: Database session
        """
        self.db = db

    # ==================== Subscription Management ====================

    async def create_subscription(
        self,
        tenant_id: UUID,
        name: str,
        url: str,
        events: list[WebhookEventType],
        custom_headers: Optional[dict] = None,
    ) -> tuple[WebhookSubscription, str]:
        """Create a new webhook subscription.

        Args:
            tenant_id: Tenant ID
            name: Human-readable name
            url: Target URL
            events: List of event types to subscribe to
            custom_headers: Optional custom headers

        Returns:
            Tuple of (subscription, secret)
        """
        # Generate a secure secret
        secret = secrets.token_hex(32)

        subscription = WebhookSubscription(
            tenant_id=tenant_id,
            name=name,
            url=str(url),
            secret=secret,
            events=[e.value for e in events],
            custom_headers=custom_headers,
        )

        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription, secret

    async def get_subscription(
        self, subscription_id: UUID, tenant_id: UUID
    ) -> Optional[WebhookSubscription]:
        """Get a webhook subscription by ID."""
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == subscription_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_subscriptions(
        self, tenant_id: UUID, include_inactive: bool = False
    ) -> list[WebhookSubscription]:
        """List all webhook subscriptions for a tenant."""
        query = select(WebhookSubscription).where(WebhookSubscription.tenant_id == tenant_id)

        if not include_inactive:
            query = query.where(WebhookSubscription.is_active.is_(True))

        query = query.order_by(WebhookSubscription.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_subscription(
        self,
        subscription_id: UUID,
        tenant_id: UUID,
        **updates,
    ) -> Optional[WebhookSubscription]:
        """Update a webhook subscription."""
        subscription = await self.get_subscription(subscription_id, tenant_id)
        if not subscription:
            return None

        for key, value in updates.items():
            if value is not None and hasattr(subscription, key):
                if key == "events":
                    # Convert enum to string values
                    value = [e.value if hasattr(e, "value") else e for e in value]
                elif key == "url":
                    value = str(value)
                setattr(subscription, key, value)

        # Reset failure count if re-enabling
        if updates.get("is_active") is True:
            subscription.failure_count = 0

        await self.db.commit()
        await self.db.refresh(subscription)
        return subscription

    async def delete_subscription(self, subscription_id: UUID, tenant_id: UUID) -> bool:
        """Delete a webhook subscription."""
        subscription = await self.get_subscription(subscription_id, tenant_id)
        if not subscription:
            return False

        await self.db.delete(subscription)
        await self.db.commit()
        return True

    async def regenerate_secret(self, subscription_id: UUID, tenant_id: UUID) -> Optional[str]:
        """Regenerate the secret for a subscription."""
        subscription = await self.get_subscription(subscription_id, tenant_id)
        if not subscription:
            return None

        new_secret = secrets.token_hex(32)
        subscription.secret = new_secret
        await self.db.commit()

        return new_secret

    # ==================== Event Delivery ====================

    async def trigger_event(
        self,
        tenant_id: UUID,
        event_type: WebhookEventType,
        data: dict[str, Any],
    ) -> list[WebhookDelivery]:
        """Trigger a webhook event for all active subscriptions.

        Args:
            tenant_id: Tenant ID
            event_type: Type of event
            data: Event data payload

        Returns:
            List of delivery records created
        """
        # Find all active subscriptions for this event
        subscriptions = await self._get_subscriptions_for_event(tenant_id, event_type)

        if not subscriptions:
            logger.debug(f"No subscriptions for event {event_type.value}")
            return []

        # Generate unique event ID
        event_id = str(uuid4())

        # Create delivery records and send webhooks
        deliveries = []
        for subscription in subscriptions:
            delivery = await self._create_delivery(
                subscription=subscription,
                event_type=event_type,
                event_id=event_id,
                data=data,
                tenant_id=tenant_id,
            )
            deliveries.append(delivery)

            # Send webhook asynchronously (don't block)
            asyncio.create_task(self._send_webhook(delivery, subscription))

        return deliveries

    async def _get_subscriptions_for_event(
        self, tenant_id: UUID, event_type: WebhookEventType
    ) -> list[WebhookSubscription]:
        """Get all active subscriptions that include this event type."""
        result = await self.db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.tenant_id == tenant_id,
                WebhookSubscription.is_active.is_(True),
            )
        )
        subscriptions = result.scalars().all()

        # Filter by event type (stored as JSON array)
        return [s for s in subscriptions if event_type.value in s.events]

    async def _create_delivery(
        self,
        subscription: WebhookSubscription,
        event_type: WebhookEventType,
        event_id: str,
        data: dict,
        tenant_id: UUID,
    ) -> WebhookDelivery:
        """Create a delivery record for tracking."""
        payload = {
            "event_id": event_id,
            "event_type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": str(tenant_id),
            "data": data,
        }

        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            event_type=event_type.value,
            event_id=event_id,
            payload=payload,
            status=DeliveryStatus.PENDING.value,
        )

        self.db.add(delivery)
        await self.db.commit()
        await self.db.refresh(delivery)

        return delivery

    async def _send_webhook(
        self,
        delivery: WebhookDelivery,
        subscription: WebhookSubscription,
    ) -> None:
        """Send webhook and update delivery status."""
        try:
            # Generate signature
            payload_bytes = json.dumps(delivery.payload).encode("utf-8")
            signature = self._generate_signature(payload_bytes, subscription.secret)

            # Build headers
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Event": delivery.event_type,
                "X-Webhook-ID": delivery.event_id,
                "User-Agent": "Nozzly-Webhook/1.0",
            }

            # Add custom headers
            if subscription.custom_headers:
                headers.update(subscription.custom_headers)

            # Send request
            start_time = datetime.now(timezone.utc)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    subscription.url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=DELIVERY_TIMEOUT_SECONDS,
                )

            response_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            # Update delivery status
            if 200 <= response.status_code < 300:
                await self._mark_success(
                    delivery,
                    subscription,
                    response.status_code,
                    response.text[:MAX_RESPONSE_BODY_LENGTH],
                    response_time_ms,
                )
            else:
                await self._mark_failed(
                    delivery,
                    subscription,
                    f"HTTP {response.status_code}",
                    response.status_code,
                    response.text[:MAX_RESPONSE_BODY_LENGTH],
                    response_time_ms,
                )

        except httpx.TimeoutException:
            await self._mark_failed(delivery, subscription, "Request timed out")
        except httpx.ConnectError as e:
            await self._mark_failed(delivery, subscription, f"Connection error: {str(e)}")
        except Exception as e:
            logger.exception(f"Webhook delivery error: {e}")
            await self._mark_failed(delivery, subscription, f"Error: {str(e)}")

    def _generate_signature(self, payload: bytes, secret: str) -> str:
        """Generate HMAC-SHA256 signature for payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

    async def _mark_success(
        self,
        delivery: WebhookDelivery,
        subscription: WebhookSubscription,
        status_code: int,
        response_body: str,
        response_time_ms: int,
    ) -> None:
        """Mark delivery as successful."""
        # Update delivery
        await self.db.execute(
            update(WebhookDelivery)
            .where(WebhookDelivery.id == delivery.id)
            .values(
                status=DeliveryStatus.SUCCESS.value,
                response_code=status_code,
                response_body=response_body,
                response_time_ms=response_time_ms,
                completed_at=datetime.now(timezone.utc),
            )
        )

        # Update subscription
        await self.db.execute(
            update(WebhookSubscription)
            .where(WebhookSubscription.id == subscription.id)
            .values(
                last_triggered_at=datetime.now(timezone.utc),
                last_success_at=datetime.now(timezone.utc),
                failure_count=0,
            )
        )

        await self.db.commit()
        logger.info(f"Webhook delivered successfully: {delivery.event_type}")

    async def _mark_failed(
        self,
        delivery: WebhookDelivery,
        subscription: WebhookSubscription,
        error_message: str,
        response_code: Optional[int] = None,
        response_body: Optional[str] = None,
        response_time_ms: Optional[int] = None,
    ) -> None:
        """Mark delivery as failed and schedule retry."""
        current_attempts = delivery.attempts

        # Check if we should retry
        if current_attempts < MAX_RETRY_ATTEMPTS:
            # Schedule retry with exponential backoff
            retry_interval = RETRY_INTERVALS[min(current_attempts - 1, len(RETRY_INTERVALS) - 1)]
            next_retry = datetime.now(timezone.utc) + timedelta(seconds=retry_interval)

            await self.db.execute(
                update(WebhookDelivery)
                .where(WebhookDelivery.id == delivery.id)
                .values(
                    status=DeliveryStatus.PENDING.value,
                    response_code=response_code,
                    response_body=response_body,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    attempts=current_attempts + 1,
                    next_retry_at=next_retry,
                )
            )
            logger.warning(
                f"Webhook delivery failed, scheduling retry {current_attempts + 1}/{MAX_RETRY_ATTEMPTS}: {error_message}"
            )
        else:
            # Final failure
            await self.db.execute(
                update(WebhookDelivery)
                .where(WebhookDelivery.id == delivery.id)
                .values(
                    status=DeliveryStatus.FAILED.value,
                    response_code=response_code,
                    response_body=response_body,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            logger.error(f"Webhook delivery failed permanently: {error_message}")

        # Update subscription failure count
        new_failure_count = subscription.failure_count + 1
        updates = {
            "last_triggered_at": datetime.now(timezone.utc),
            "failure_count": new_failure_count,
        }

        # Auto-disable if threshold reached
        if new_failure_count >= FAILURE_DISABLE_THRESHOLD:
            updates["is_active"] = False
            logger.warning(
                f"Webhook subscription {subscription.id} disabled after {new_failure_count} failures"
            )

        await self.db.execute(
            update(WebhookSubscription)
            .where(WebhookSubscription.id == subscription.id)
            .values(**updates)
        )

        await self.db.commit()

    # ==================== Delivery Management ====================

    async def list_deliveries(
        self,
        tenant_id: UUID,
        subscription_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        status: Optional[DeliveryStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[WebhookDelivery], int]:
        """List webhook deliveries with filtering."""
        # Build base query through subscriptions for tenant isolation
        query = (
            select(WebhookDelivery)
            .join(WebhookSubscription)
            .where(WebhookSubscription.tenant_id == tenant_id)
        )

        if subscription_id:
            query = query.where(WebhookDelivery.subscription_id == subscription_id)
        if event_type:
            query = query.where(WebhookDelivery.event_type == event_type)
        if status:
            query = query.where(WebhookDelivery.status == status.value)

        # Get total count
        from sqlalchemy import func

        count_query = (
            select(func.count())
            .select_from(WebhookDelivery)
            .join(WebhookSubscription)
            .where(WebhookSubscription.tenant_id == tenant_id)
        )
        if subscription_id:
            count_query = count_query.where(WebhookDelivery.subscription_id == subscription_id)
        if event_type:
            count_query = count_query.where(WebhookDelivery.event_type == event_type)
        if status:
            count_query = count_query.where(WebhookDelivery.status == status.value)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get deliveries
        query = query.order_by(WebhookDelivery.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        deliveries = list(result.scalars().all())

        return deliveries, total

    async def get_delivery(self, delivery_id: UUID, tenant_id: UUID) -> Optional[WebhookDelivery]:
        """Get a specific delivery by ID."""
        result = await self.db.execute(
            select(WebhookDelivery)
            .join(WebhookSubscription)
            .where(
                WebhookDelivery.id == delivery_id,
                WebhookSubscription.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def retry_delivery(self, delivery_id: UUID, tenant_id: UUID) -> Optional[WebhookDelivery]:
        """Manually retry a failed delivery."""
        delivery = await self.get_delivery(delivery_id, tenant_id)
        if not delivery:
            return None

        if delivery.status != DeliveryStatus.FAILED.value:
            raise ValueError("Can only retry failed deliveries")

        # Get subscription
        subscription = await self.get_subscription(delivery.subscription_id, tenant_id)
        if not subscription or not subscription.is_active:
            raise ValueError("Subscription is inactive")

        # Reset delivery for retry
        delivery.status = DeliveryStatus.PENDING.value
        delivery.attempts = 1
        delivery.next_retry_at = None
        delivery.error_message = None
        delivery.completed_at = None

        await self.db.commit()

        # Send webhook
        asyncio.create_task(self._send_webhook(delivery, subscription))

        return delivery

    # ==================== Testing ====================

    async def test_webhook(
        self,
        subscription_id: UUID,
        tenant_id: UUID,
        event_type: WebhookEventType = WebhookEventType.ORDER_CREATED,
        test_data: Optional[dict] = None,
    ) -> dict:
        """Send a test webhook to verify configuration."""
        subscription = await self.get_subscription(subscription_id, tenant_id)
        if not subscription:
            raise ValueError("Subscription not found")

        # Build test payload
        payload = {
            "event_id": str(uuid4()),
            "event_type": f"test.{event_type.value}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": str(tenant_id),
            "data": test_data or {"message": "This is a test webhook"},
            "test": True,
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = self._generate_signature(payload_bytes, subscription.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": f"test.{event_type.value}",
            "X-Webhook-ID": payload["event_id"],
            "User-Agent": "Nozzly-Webhook/1.0",
        }

        if subscription.custom_headers:
            headers.update(subscription.custom_headers)

        try:
            start_time = datetime.now(timezone.utc)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    subscription.url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=DELIVERY_TIMEOUT_SECONDS,
                )

            response_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            return {
                "success": 200 <= response.status_code < 300,
                "response_code": response.status_code,
                "response_time_ms": response_time_ms,
                "response_body": response.text[:MAX_RESPONSE_BODY_LENGTH],
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error_message": "Request timed out",
            }
        except httpx.ConnectError as e:
            return {
                "success": False,
                "error_message": f"Connection error: {str(e)}",
            }
        except Exception as e:
            return {
                "success": False,
                "error_message": f"Error: {str(e)}",
            }


# ==================== Helper Functions ====================


async def trigger_webhook_event(
    db: AsyncSession,
    tenant_id: UUID,
    event_type: WebhookEventType,
    data: dict[str, Any],
) -> None:
    """Convenience function to trigger a webhook event.

    Use this from other services to trigger webhooks without
    needing to instantiate WebhookService directly.
    """
    service = WebhookService(db)
    await service.trigger_event(tenant_id, event_type, data)
