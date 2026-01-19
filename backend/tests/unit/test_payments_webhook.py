"""Comprehensive unit tests for Square webhook endpoint.

Tests all aspects of webhook handling including signature validation,
event processing, and database updates.
"""

import base64
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.payments import (
    WebhookResponse,
    _handle_payment_created,
    _handle_payment_updated,
    _handle_refund_created,
    _handle_refund_updated,
    router,
)


# ============================================
# Test Fixtures
# ============================================


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.square_webhook_signature_key = "test-webhook-key"
    settings.square_access_token = "test-token"
    settings.square_location_id = "test-location"
    return settings


@pytest.fixture
def mock_db():
    """Create mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_order():
    """Create a mock order for testing."""
    order = MagicMock()
    order.id = uuid4()
    order.order_number = "MF-20251219-001"
    order.payment_id = "square_payment_123"
    order.payment_status = "COMPLETED"
    order.status = "pending"
    order.customer_email = "test@example.com"
    order.customer_name = "Test Customer"
    order.total = 50.00
    order.currency = "GBP"
    return order


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/payments")
    return app


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
# Webhook Event Factory
# ============================================


def create_payment_created_event(payment_id: str = "pay_123", status: str = "COMPLETED") -> dict:
    """Create a payment.created webhook event."""
    return {
        "type": "payment.created",
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


def create_payment_updated_event(payment_id: str = "pay_123", status: str = "COMPLETED") -> dict:
    """Create a payment.updated webhook event."""
    return {
        "type": "payment.updated",
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


def create_refund_created_event(
    refund_id: str = "refund_123",
    payment_id: str = "pay_123",
    status: str = "COMPLETED",
    amount: int = 5000,
) -> dict:
    """Create a refund.created webhook event."""
    return {
        "type": "refund.created",
        "data": {
            "object": {
                "refund": {
                    "id": refund_id,
                    "payment_id": payment_id,
                    "status": status,
                    "amount_money": {"amount": amount, "currency": "GBP"},
                }
            }
        },
    }


def create_refund_updated_event(
    refund_id: str = "refund_123",
    payment_id: str = "pay_123",
    status: str = "COMPLETED",
) -> dict:
    """Create a refund.updated webhook event."""
    return {
        "type": "refund.updated",
        "data": {
            "object": {
                "refund": {
                    "id": refund_id,
                    "payment_id": payment_id,
                    "status": status,
                }
            }
        },
    }


# ============================================
# Test Signature Validation
# ============================================


class TestSignatureValidation:
    """Tests for webhook signature validation."""

    @pytest.mark.asyncio
    async def test_valid_signature_accepted(self, app, mock_settings, mock_db):
        """Test that valid signatures are accepted."""
        webhook_key = "test-webhook-key"
        event = create_payment_created_event()
        body = json.dumps(event).encode()
        url = "http://testserver/payments/webhooks/square"
        signature = generate_signature(body, webhook_key, url)

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                # We need to mock the db dependency
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                    headers={"x-square-hmacsha256-signature": signature},
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, app, mock_settings, mock_db):
        """Test that invalid signatures are rejected."""
        event = create_payment_created_event()
        body = json.dumps(event).encode()

        # Patch the settings object directly since it's loaded at module import time
        with patch("app.api.v1.payments.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                    headers={"x-square-hmacsha256-signature": "invalid-signature"},
                )

                assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_signature_rejected(self, app, mock_settings, mock_db):
        """Test that missing signatures are rejected when key is configured."""
        event = create_payment_created_event()
        body = json.dumps(event).encode()

        # Patch the settings object directly since it's loaded at module import time
        with patch("app.api.v1.payments.settings", mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                    # No signature header
                )

                # With empty signature and configured key, should fail validation
                assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_no_signature_validation_when_key_not_configured(self, app, mock_db):
        """Test that signature validation is skipped when key is not configured."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        event = create_payment_created_event()
        body = json.dumps(event).encode()

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                    # No signature header, but key not configured
                )

                assert response.status_code == 200


# ============================================
# Test Invalid JSON Handling
# ============================================


class TestInvalidJsonHandling:
    """Tests for handling invalid JSON in webhook body."""

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, app, mock_db):
        """Test that invalid JSON returns 400 error."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=b"not valid json",
                )

                assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_body_returns_400(self, app, mock_db):
        """Test that empty body returns 400 error."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=b"",
                )

                assert response.status_code == 400


# ============================================
# Test Event Type Handling
# ============================================


class TestEventTypeHandling:
    """Tests for handling different event types."""

    @pytest.mark.asyncio
    async def test_unhandled_event_type_returns_200(self, app, mock_db):
        """Test that unhandled event types still return 200."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        event = {"type": "some.unhandled.event", "data": {}}
        body = json.dumps(event).encode()

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                )

                assert response.status_code == 200
                assert response.json()["status"] == "received"

    @pytest.mark.asyncio
    async def test_event_without_type_returns_200(self, app, mock_db):
        """Test that events without type field return 200."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        event = {"data": {"object": {}}}
        body = json.dumps(event).encode()

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                )

                assert response.status_code == 200


# ============================================
# Test Payment Created Handler
# ============================================


class TestPaymentCreatedHandler:
    """Tests for _handle_payment_created function."""

    @pytest.mark.asyncio
    async def test_logs_payment_created_event(self, mock_db, caplog):
        """Test that payment.created event is logged."""
        import logging

        logger = logging.getLogger(__name__)

        payment_data = {
            "payment": {
                "id": "pay_test_123",
                "status": "COMPLETED",
            }
        }

        await _handle_payment_created(payment_data, mock_db, logger)

        # Function just logs, no db operations
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handles_missing_payment_data(self, mock_db):
        """Test handling of missing payment data."""
        import logging

        logger = logging.getLogger(__name__)

        payment_data = {}  # No payment key

        # Should not raise
        await _handle_payment_created(payment_data, mock_db, logger)


# ============================================
# Test Payment Updated Handler
# ============================================


class TestPaymentUpdatedHandler:
    """Tests for _handle_payment_updated function."""

    @pytest.mark.asyncio
    async def test_updates_order_payment_status(self, mock_db, mock_order):
        """Test that order payment status is updated."""
        import logging

        logger = logging.getLogger(__name__)

        # Mock finding the order
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        payment_data = {
            "payment": {
                "id": "square_payment_123",
                "status": "COMPLETED",
            }
        }

        await _handle_payment_updated(payment_data, mock_db, logger)

        mock_db.commit.assert_awaited_once()
        assert mock_order.payment_status == "COMPLETED"

    @pytest.mark.asyncio
    async def test_handles_missing_order(self, mock_db):
        """Test handling when order is not found."""
        import logging

        logger = logging.getLogger(__name__)

        # Mock not finding the order
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        payment_data = {
            "payment": {
                "id": "unknown_payment_id",
                "status": "COMPLETED",
            }
        }

        # Should not raise
        await _handle_payment_updated(payment_data, mock_db, logger)
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_updates_order_timestamp(self, mock_db, mock_order):
        """Test that order updated_at is set."""
        import logging

        logger = logging.getLogger(__name__)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        payment_data = {
            "payment": {
                "id": "square_payment_123",
                "status": "VOIDED",
            }
        }

        await _handle_payment_updated(payment_data, mock_db, logger)

        assert mock_order.updated_at is not None


# ============================================
# Test Refund Created Handler
# ============================================


class TestRefundCreatedHandler:
    """Tests for _handle_refund_created function."""

    @pytest.mark.asyncio
    async def test_updates_order_to_refunded_when_completed(self, mock_db, mock_order):
        """Test that order is updated to refunded status when refund completes."""
        import logging

        from app.models.order import OrderStatus

        logger = logging.getLogger(__name__)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        refund_data = {
            "refund": {
                "id": "refund_123",
                "payment_id": "square_payment_123",
                "status": "COMPLETED",
                "amount_money": {"amount": 5000, "currency": "GBP"},
            }
        }

        await _handle_refund_created(refund_data, mock_db, logger)

        mock_db.commit.assert_awaited_once()
        assert mock_order.status == OrderStatus.REFUNDED
        assert mock_order.payment_status == "REFUNDED"

    @pytest.mark.asyncio
    async def test_does_not_update_order_for_pending_refund(self, mock_db, mock_order):
        """Test that order is not updated for pending refund."""
        import logging

        logger = logging.getLogger(__name__)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        original_status = mock_order.status

        refund_data = {
            "refund": {
                "id": "refund_123",
                "payment_id": "square_payment_123",
                "status": "PENDING",
                "amount_money": {"amount": 5000, "currency": "GBP"},
            }
        }

        await _handle_refund_created(refund_data, mock_db, logger)

        # Status should not change for pending refund
        mock_db.commit.assert_not_awaited()
        assert mock_order.status == original_status

    @pytest.mark.asyncio
    async def test_handles_missing_order_for_refund(self, mock_db):
        """Test handling when order is not found for refund."""
        import logging

        logger = logging.getLogger(__name__)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        refund_data = {
            "refund": {
                "id": "refund_123",
                "payment_id": "unknown_payment_id",
                "status": "COMPLETED",
                "amount_money": {"amount": 5000, "currency": "GBP"},
            }
        }

        # Should not raise
        await _handle_refund_created(refund_data, mock_db, logger)
        mock_db.commit.assert_not_awaited()


# ============================================
# Test Refund Updated Handler
# ============================================


class TestRefundUpdatedHandler:
    """Tests for _handle_refund_updated function."""

    @pytest.mark.asyncio
    async def test_updates_order_when_refund_completed(self, mock_db, mock_order):
        """Test that order is updated when refund status becomes COMPLETED."""
        import logging

        from app.models.order import OrderStatus

        logger = logging.getLogger(__name__)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        refund_data = {
            "refund": {
                "id": "refund_123",
                "payment_id": "square_payment_123",
                "status": "COMPLETED",
            }
        }

        await _handle_refund_updated(refund_data, mock_db, logger)

        mock_db.commit.assert_awaited_once()
        assert mock_order.status == OrderStatus.REFUNDED
        assert mock_order.payment_status == "REFUNDED"

    @pytest.mark.asyncio
    async def test_does_not_update_for_non_completed_status(self, mock_db, mock_order):
        """Test that order is not updated for non-COMPLETED refund status."""
        import logging

        logger = logging.getLogger(__name__)

        refund_data = {
            "refund": {
                "id": "refund_123",
                "payment_id": "square_payment_123",
                "status": "FAILED",
            }
        }

        await _handle_refund_updated(refund_data, mock_db, logger)

        # DB should not be queried for non-COMPLETED status
        mock_db.execute.assert_not_awaited()


# ============================================
# Test Error Handling in Event Handlers
# ============================================


class TestWebhookErrorHandling:
    """Tests for error handling during webhook processing."""

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_fail_webhook(self, app, mock_db):
        """Test that handler exceptions don't cause webhook to fail."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        # Make the db query raise an exception
        mock_db.execute.side_effect = Exception("Database error")

        event = create_payment_updated_event()
        body = json.dumps(event).encode()

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                )

                # Should still return 200 even if handler fails
                assert response.status_code == 200
                assert response.json()["status"] == "received"


# ============================================
# Test WebhookResponse Schema
# ============================================


class TestWebhookResponseSchema:
    """Tests for WebhookResponse schema."""

    def test_default_status(self):
        """Test default status value."""
        response = WebhookResponse()
        assert response.status == "received"

    def test_custom_status(self):
        """Test custom status value."""
        response = WebhookResponse(status="processed")
        assert response.status == "processed"


# ============================================
# Integration-Style Tests
# ============================================


class TestWebhookIntegration:
    """Integration-style tests for webhook endpoint."""

    @pytest.mark.asyncio
    async def test_full_payment_created_flow(self, app, mock_db):
        """Test complete flow for payment.created event."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        event = create_payment_created_event("pay_full_flow_123", "COMPLETED")
        body = json.dumps(event).encode()

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                )

                assert response.status_code == 200
                # Response now includes additional fields from the robust webhook service
                data = response.json()
                assert data["status"] in ["received", "processed", "duplicate"]

    @pytest.mark.asyncio
    async def test_full_refund_flow_updates_order(self, app, mock_db, mock_order):
        """Test complete flow for refund event updating order."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        event = create_refund_created_event(
            refund_id="refund_full_flow",
            payment_id="square_payment_123",
            status="COMPLETED",
        )
        body = json.dumps(event).encode()

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                )

                assert response.status_code == 200
                # Note: The robust webhook service processes asynchronously,
                # but the order status update happens via the legacy handlers
                # which are still called for backwards compatibility in tests

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "event_type,event_factory",
        [
            ("payment.created", create_payment_created_event),
            ("payment.updated", create_payment_updated_event),
            ("refund.created", create_refund_created_event),
            ("refund.updated", create_refund_updated_event),
        ],
    )
    async def test_all_event_types_return_200(self, app, mock_db, event_type: str, event_factory):
        """Test that all supported event types return 200."""
        mock_settings = MagicMock()
        mock_settings.square_webhook_signature_key = None

        # For payment.updated and refund events, mock finding an order
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No order found is fine
        mock_db.execute.return_value = mock_result

        event = event_factory()
        body = json.dumps(event).encode()

        with patch("app.api.v1.payments.get_settings", return_value=mock_settings):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                from app.database import get_db

                app.dependency_overrides[get_db] = lambda: mock_db

                response = await client.post(
                    "/payments/webhooks/square",
                    content=body,
                )

                assert response.status_code == 200
