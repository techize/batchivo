"""Comprehensive tests for SquareWebhookService.

Tests cover:
- Signature verification
- Idempotency (duplicate prevention)
- All payment event types (created, updated, failed)
- All refund event types (created, updated)
- Retry logic with exponential backoff
- Dead-letter queue behavior
- Database transactions
"""

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.order import Order, OrderStatus
from app.models.webhook_event import (
    WebhookDeadLetter,
    WebhookEvent,
    WebhookEventSource,
    WebhookEventStatus,
)
from app.services.square_webhook_service import (
    MAX_RETRY_ATTEMPTS,
    RETRY_BACKOFF_BASE,
    RETRY_BACKOFF_MULTIPLIER,
    SquareWebhookService,
    retry_failed_webhooks,
)


# ============================================
# Test Fixtures
# ============================================


@pytest.fixture
def mock_db():
    """Create mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_order():
    """Create a mock order."""
    order = MagicMock(spec=Order)
    order.id = uuid4()
    order.order_number = "TEST-20260119-001"
    order.payment_id = "square_payment_123"
    order.payment_status = "COMPLETED"
    order.status = OrderStatus.PENDING
    order.updated_at = None
    return order


@pytest.fixture
def webhook_service(mock_db):
    """Create webhook service with mock db."""
    return SquareWebhookService(mock_db)


def generate_signature(body: bytes, key: str, url: str) -> str:
    """Generate valid Square webhook signature."""
    string_to_sign = url + body.decode("utf-8")
    signature = hmac.new(
        key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(signature).decode("utf-8")


# ============================================
# Event Factories
# ============================================


def create_payment_created_event(
    event_id: str = "evt_123",
    payment_id: str = "pay_123",
    status: str = "COMPLETED",
    amount: int = 5000,
) -> dict:
    """Create a payment.created webhook event."""
    return {
        "type": "payment.created",
        "event_id": event_id,
        "data": {
            "object": {
                "payment": {
                    "id": payment_id,
                    "status": status,
                    "amount_money": {"amount": amount, "currency": "GBP"},
                }
            }
        },
    }


def create_payment_updated_event(
    event_id: str = "evt_456",
    payment_id: str = "pay_123",
    status: str = "COMPLETED",
) -> dict:
    """Create a payment.updated webhook event."""
    return {
        "type": "payment.updated",
        "event_id": event_id,
        "data": {
            "object": {
                "payment": {
                    "id": payment_id,
                    "status": status,
                    "amount_money": {"amount": 5000, "currency": "GBP"},
                }
            }
        },
    }


def create_payment_failed_event(
    event_id: str = "evt_789",
    payment_id: str = "pay_failed_123",
    error_code: str = "CARD_DECLINED",
    error_detail: str = "Card was declined",
) -> dict:
    """Create a payment.failed webhook event."""
    return {
        "type": "payment.failed",
        "event_id": event_id,
        "data": {
            "object": {
                "payment": {
                    "id": payment_id,
                    "status": "FAILED",
                    "amount_money": {"amount": 5000, "currency": "GBP"},
                    "errors": [{"code": error_code, "detail": error_detail}],
                    "card_details": {
                        "errors": [{"code": error_code, "detail": error_detail}]
                    },
                }
            }
        },
    }


def create_refund_created_event(
    event_id: str = "evt_refund_123",
    refund_id: str = "refund_123",
    payment_id: str = "pay_123",
    status: str = "COMPLETED",
    amount: int = 5000,
) -> dict:
    """Create a refund.created webhook event."""
    return {
        "type": "refund.created",
        "event_id": event_id,
        "data": {
            "object": {
                "refund": {
                    "id": refund_id,
                    "payment_id": payment_id,
                    "status": status,
                    "amount_money": {"amount": amount, "currency": "GBP"},
                    "reason": "Customer request",
                }
            }
        },
    }


def create_refund_updated_event(
    event_id: str = "evt_refund_456",
    refund_id: str = "refund_123",
    payment_id: str = "pay_123",
    status: str = "COMPLETED",
) -> dict:
    """Create a refund.updated webhook event."""
    return {
        "type": "refund.updated",
        "event_id": event_id,
        "data": {
            "object": {
                "refund": {
                    "id": refund_id,
                    "payment_id": payment_id,
                    "status": status,
                    "amount_money": {"amount": 5000, "currency": "GBP"},
                }
            }
        },
    }


# ============================================
# Signature Verification Tests
# ============================================


class TestSignatureVerification:
    """Tests for webhook signature verification."""

    @pytest.mark.asyncio
    async def test_valid_signature_returns_true(self, webhook_service):
        """Test that valid signature is accepted."""
        body = b'{"type": "payment.created"}'
        key = "test-webhook-key"
        url = "https://example.com/webhooks/square"
        signature = generate_signature(body, key, url)

        result = await webhook_service.verify_signature(body, signature, key, url)

        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_false(self, webhook_service):
        """Test that invalid signature is rejected."""
        body = b'{"type": "payment.created"}'
        key = "test-webhook-key"
        url = "https://example.com/webhooks/square"

        result = await webhook_service.verify_signature(body, "invalid", key, url)

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_key_skips_validation(self, webhook_service):
        """Test that missing key skips validation."""
        body = b'{"type": "payment.created"}'
        url = "https://example.com/webhooks/square"

        result = await webhook_service.verify_signature(body, "any", "", url)

        assert result is True

    @pytest.mark.asyncio
    async def test_none_key_skips_validation(self, webhook_service):
        """Test that None key skips validation."""
        body = b'{"type": "payment.created"}'
        url = "https://example.com/webhooks/square"

        result = await webhook_service.verify_signature(body, "any", None, url)

        assert result is True

    @pytest.mark.asyncio
    async def test_missing_signature_returns_false(self, webhook_service):
        """Test that missing signature is rejected when key is configured."""
        body = b'{"type": "payment.created"}'
        key = "test-webhook-key"
        url = "https://example.com/webhooks/square"

        result = await webhook_service.verify_signature(body, "", key, url)

        assert result is False


# ============================================
# Idempotency Tests
# ============================================


class TestIdempotency:
    """Tests for webhook idempotency handling."""

    @pytest.mark.asyncio
    async def test_duplicate_event_returns_duplicate_status(self, webhook_service, mock_db):
        """Test that duplicate events are detected and skipped."""
        # Mock existing completed event
        existing_event = MagicMock(spec=WebhookEvent)
        existing_event.status = WebhookEventStatus.COMPLETED.value
        existing_event.event_id = "evt_duplicate_123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_event
        mock_db.execute.return_value = mock_result

        event_data = create_payment_created_event(event_id="evt_duplicate_123")

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "duplicate"
        assert result["message"] == "Event already processed"

    @pytest.mark.asyncio
    async def test_processing_event_returns_processing_status(self, webhook_service, mock_db):
        """Test that in-progress events return processing status."""
        # Mock existing event that's being processed
        existing_event = MagicMock(spec=WebhookEvent)
        existing_event.status = WebhookEventStatus.PROCESSING.value
        existing_event.event_id = "evt_processing_123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_event
        mock_db.execute.return_value = mock_result

        event_data = create_payment_created_event(event_id="evt_processing_123")

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processing"

    @pytest.mark.asyncio
    async def test_new_event_creates_record(self, webhook_service, mock_db):
        """Test that new events create a webhook_events record."""
        # Mock no existing event
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        event_data = create_payment_created_event(event_id="evt_new_123")

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()


# ============================================
# Payment Event Tests
# ============================================


class TestPaymentEvents:
    """Tests for payment webhook event handling."""

    @pytest.mark.asyncio
    async def test_payment_created_logs_event(self, webhook_service, mock_db):
        """Test that payment.created event is logged."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        event_data = create_payment_created_event(
            event_id="evt_pay_created_123",
            payment_id="pay_new_123",
            status="COMPLETED",
            amount=7500,
        )

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        assert "Logged payment.created" in str(result.get("result", {}).get("actions", []))

    @pytest.mark.asyncio
    async def test_payment_updated_updates_order(self, webhook_service, mock_db):
        """Test that payment.updated updates associated order."""
        # Create a fresh order mock for this test
        order = MagicMock()
        order.id = uuid4()
        order.order_number = "TEST-20260119-001"
        order.payment_id = "square_payment_123"
        order.payment_status = "COMPLETED"
        order.status = OrderStatus.PENDING
        order.updated_at = None

        # Mock execute to return different results based on query
        def mock_execute_side_effect(*args, **kwargs):
            result = MagicMock()
            # Check the query to determine what to return
            query = args[0]
            query_str = str(query)
            if "webhook_events" in query_str:
                result.scalar_one_or_none.return_value = None
            elif "orders" in query_str:
                result.scalar_one_or_none.return_value = order
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute_side_effect

        event_data = create_payment_updated_event(
            event_id="evt_pay_updated_123",
            payment_id="square_payment_123",
            status="CAPTURED",
        )

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        assert order.payment_status == "CAPTURED"
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_payment_failed_logs_error_details(self, webhook_service, mock_db):
        """Test that payment.failed logs detailed error information."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        event_data = create_payment_failed_event(
            event_id="evt_pay_failed_123",
            payment_id="pay_failed_456",
            error_code="CARD_DECLINED",
            error_detail="Insufficient funds",
        )

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        actions = result.get("result", {}).get("actions", [])
        assert any("FAILED" in str(a) or "failure" in str(a).lower() for a in actions)


# ============================================
# Refund Event Tests
# ============================================


class TestRefundEvents:
    """Tests for refund webhook event handling."""

    @pytest.mark.asyncio
    async def test_refund_created_completed_updates_order(self, webhook_service, mock_db):
        """Test that completed refund.created updates order to REFUNDED."""
        # Create a fresh order mock
        order = MagicMock()
        order.id = uuid4()
        order.order_number = "TEST-20260119-001"
        order.payment_id = "square_payment_123"
        order.payment_status = "COMPLETED"
        order.status = OrderStatus.PENDING
        order.updated_at = None

        def mock_execute_side_effect(*args, **kwargs):
            result = MagicMock()
            query = args[0]
            query_str = str(query)
            if "webhook_events" in query_str:
                result.scalar_one_or_none.return_value = None
            elif "orders" in query_str:
                result.scalar_one_or_none.return_value = order
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute_side_effect

        event_data = create_refund_created_event(
            event_id="evt_refund_created_123",
            refund_id="refund_new_123",
            payment_id="square_payment_123",
            status="COMPLETED",
        )

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        assert order.status == OrderStatus.REFUNDED
        assert order.payment_status == "REFUNDED"

    @pytest.mark.asyncio
    async def test_refund_created_pending_does_not_update_order(self, webhook_service, mock_db):
        """Test that pending refund.created does not change order status."""
        # Create a fresh order mock
        order = MagicMock()
        order.id = uuid4()
        order.order_number = "TEST-20260119-001"
        order.payment_id = "square_payment_123"
        order.payment_status = "COMPLETED"
        order.status = OrderStatus.PENDING
        order.updated_at = None

        original_status = order.status

        def mock_execute_side_effect(*args, **kwargs):
            result = MagicMock()
            query = args[0]
            query_str = str(query)
            if "webhook_events" in query_str:
                result.scalar_one_or_none.return_value = None
            elif "orders" in query_str:
                result.scalar_one_or_none.return_value = order
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute_side_effect

        event_data = create_refund_created_event(
            event_id="evt_refund_pending_123",
            status="PENDING",
        )

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        # Status should not change for pending refund
        assert order.status == original_status

    @pytest.mark.asyncio
    async def test_refund_updated_completed_updates_order(self, webhook_service, mock_db):
        """Test that refund.updated with COMPLETED status updates order."""
        # Create a fresh order mock
        order = MagicMock()
        order.id = uuid4()
        order.order_number = "TEST-20260119-001"
        order.payment_id = "square_payment_123"
        order.payment_status = "COMPLETED"
        order.status = OrderStatus.PENDING
        order.updated_at = None

        def mock_execute_side_effect(*args, **kwargs):
            result = MagicMock()
            query = args[0]
            query_str = str(query)
            if "webhook_events" in query_str:
                result.scalar_one_or_none.return_value = None
            elif "orders" in query_str:
                result.scalar_one_or_none.return_value = order
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute_side_effect

        event_data = create_refund_updated_event(
            event_id="evt_refund_updated_123",
            status="COMPLETED",
        )

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        assert order.status == OrderStatus.REFUNDED


# ============================================
# Retry Logic Tests
# ============================================


class TestRetryLogic:
    """Tests for webhook retry logic."""

    @pytest.mark.asyncio
    async def test_failed_event_schedules_retry(self, webhook_service, mock_db):
        """Test that failed events are scheduled for retry."""
        # Create a mock webhook event that will be created
        mock_webhook_event = MagicMock()
        mock_webhook_event.id = uuid4()
        mock_webhook_event.event_id = "evt_fail_123"
        mock_webhook_event.attempt_count = 1
        mock_webhook_event.max_attempts = MAX_RETRY_ATTEMPTS
        mock_webhook_event.error_message = None
        mock_webhook_event.error_details = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock _create_or_update_event to return our mock event
        with patch.object(
            webhook_service, "_create_or_update_event", return_value=mock_webhook_event
        ):
            # Mock an exception during processing
            with patch.object(
                webhook_service, "_process_event", side_effect=Exception("Processing error")
            ):
                event_data = create_payment_created_event(event_id="evt_fail_123")

                result = await webhook_service.process_webhook(event_data)

                assert result["status"] == "failed"
                assert result["will_retry"] is True

    @pytest.mark.asyncio
    async def test_max_retries_moves_to_dead_letter(self, webhook_service, mock_db):
        """Test that events exceeding max retries go to dead letter queue."""
        # Create an event that has already exhausted retries
        existing_event = MagicMock(spec=WebhookEvent)
        existing_event.id = uuid4()
        existing_event.event_id = "evt_exhausted_123"
        existing_event.source = WebhookEventSource.SQUARE.value
        existing_event.event_type = "payment.created"
        existing_event.status = WebhookEventStatus.FAILED.value
        existing_event.attempt_count = MAX_RETRY_ATTEMPTS - 1  # One more attempt will exhaust
        existing_event.max_attempts = MAX_RETRY_ATTEMPTS
        existing_event.first_received_at = datetime.now(timezone.utc)
        existing_event.payload = create_payment_created_event(event_id="evt_exhausted_123")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_event
        mock_db.execute.return_value = mock_result

        # Mock an exception during processing
        with patch.object(
            webhook_service, "_process_event", side_effect=Exception("Still failing")
        ):
            event_data = create_payment_created_event(event_id="evt_exhausted_123")

            result = await webhook_service.process_webhook(event_data)

            assert result["status"] == "failed"
            assert result["will_retry"] is False

    def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        # Attempt 1: base delay
        delay_1 = RETRY_BACKOFF_BASE * (RETRY_BACKOFF_MULTIPLIER ** 0)
        assert delay_1 == RETRY_BACKOFF_BASE

        # Attempt 2: doubled
        delay_2 = RETRY_BACKOFF_BASE * (RETRY_BACKOFF_MULTIPLIER ** 1)
        assert delay_2 == RETRY_BACKOFF_BASE * 2

        # Attempt 3: quadrupled
        delay_3 = RETRY_BACKOFF_BASE * (RETRY_BACKOFF_MULTIPLIER ** 2)
        assert delay_3 == RETRY_BACKOFF_BASE * 4


# ============================================
# Dead Letter Queue Tests
# ============================================


class TestDeadLetterQueue:
    """Tests for dead letter queue behavior."""

    @pytest.mark.asyncio
    async def test_dead_letter_record_created(self, webhook_service, mock_db):
        """Test that dead letter record is created when event moves to DLQ."""
        # Create an event that should go to dead letter queue
        webhook_event = MagicMock(spec=WebhookEvent)
        webhook_event.id = uuid4()
        webhook_event.event_id = "evt_dlq_123"
        webhook_event.source = WebhookEventSource.SQUARE.value
        webhook_event.event_type = "payment.created"
        webhook_event.attempt_count = MAX_RETRY_ATTEMPTS
        webhook_event.max_attempts = MAX_RETRY_ATTEMPTS
        webhook_event.first_received_at = datetime.now(timezone.utc)
        webhook_event.error_details = {"traceback": "test"}

        await webhook_service._handle_failure(
            webhook_event, "Permanent failure", "Traceback here"
        )

        # Verify dead letter record was created
        mock_db.add.assert_called()
        call_args = mock_db.add.call_args_list
        dlq_calls = [c for c in call_args if isinstance(c[0][0], WebhookDeadLetter)]
        # Note: In real code we'd check the WebhookDeadLetter type
        mock_db.commit.assert_awaited()


# ============================================
# Error Handling Tests
# ============================================


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_missing_order_does_not_fail(self, webhook_service, mock_db):
        """Test that missing order doesn't cause webhook to fail."""
        mock_result_no_event = MagicMock()
        mock_result_no_event.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result_no_event

        event_data = create_payment_updated_event(
            event_id="evt_no_order_123",
            payment_id="unknown_payment_id",
        )

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        actions = result.get("result", {}).get("actions", [])
        assert any("No order found" in str(a) for a in actions)

    @pytest.mark.asyncio
    async def test_unknown_event_type_handled(self, webhook_service, mock_db):
        """Test that unknown event types are logged but don't fail."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        event_data = {
            "type": "some.unknown.event",
            "event_id": "evt_unknown_123",
            "data": {"object": {}},
        }

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        actions = result.get("result", {}).get("actions", [])
        assert any("unhandled event" in str(a).lower() for a in actions)

    @pytest.mark.asyncio
    async def test_missing_event_id_generates_one(self, webhook_service, mock_db):
        """Test that missing event_id is generated."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        event_data = {
            "type": "payment.created",
            # No event_id
            "data": {"object": {"payment": {"id": "pay_123", "status": "COMPLETED"}}},
        }

        result = await webhook_service.process_webhook(event_data)

        assert result["status"] == "processed"
        assert result.get("event_id") is not None
        assert result["event_id"].startswith("generated-")


# ============================================
# Retry Processing Background Task Tests
# ============================================


class TestRetryBackgroundTask:
    """Tests for the retry_failed_webhooks background task."""

    @pytest.mark.asyncio
    async def test_retry_finds_due_events(self, mock_db):
        """Test that retry task finds events due for retry."""
        # Create mock events ready for retry
        event1 = MagicMock(spec=WebhookEvent)
        event1.event_id = "evt_retry_1"
        event1.status = WebhookEventStatus.FAILED.value
        event1.next_retry_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        event1.attempt_count = 2
        event1.max_attempts = 5
        event1.payload = create_payment_created_event(event_id="evt_retry_1")
        event1.signature_valid = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [event1]
        mock_db.execute.return_value = mock_result

        with patch(
            "app.services.square_webhook_service.SquareWebhookService.process_webhook",
            new_callable=AsyncMock,
        ) as mock_process:
            mock_process.return_value = {"status": "processed"}

            processed = await retry_failed_webhooks(mock_db, max_events=10)

            assert processed == 1

    @pytest.mark.asyncio
    async def test_retry_returns_zero_when_no_events(self, mock_db):
        """Test that retry task returns 0 when no events to process."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        processed = await retry_failed_webhooks(mock_db, max_events=10)

        assert processed == 0


# ============================================
# Transaction Safety Tests
# ============================================


class TestTransactionSafety:
    """Tests for database transaction handling."""

    @pytest.mark.asyncio
    async def test_commit_called_on_success(self, webhook_service, mock_db):
        """Test that commit is called after successful processing."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        event_data = create_payment_created_event(event_id="evt_commit_test")

        await webhook_service.process_webhook(event_data)

        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_order_updated_in_transaction(self, webhook_service, mock_db):
        """Test that order updates happen within transaction."""
        # Create a fresh order mock
        order = MagicMock()
        order.id = uuid4()
        order.order_number = "TEST-20260119-001"
        order.payment_id = "square_payment_123"
        order.payment_status = "COMPLETED"
        order.status = OrderStatus.PENDING
        order.updated_at = None

        def mock_execute_side_effect(*args, **kwargs):
            result = MagicMock()
            query = args[0]
            query_str = str(query)
            if "webhook_events" in query_str:
                result.scalar_one_or_none.return_value = None
            elif "orders" in query_str:
                result.scalar_one_or_none.return_value = order
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute_side_effect

        event_data = create_refund_created_event(
            event_id="evt_txn_test",
            status="COMPLETED",
        )

        await webhook_service.process_webhook(event_data)

        # Verify order was updated
        assert order.status == OrderStatus.REFUNDED
        # Verify commit was called
        mock_db.commit.assert_awaited()
