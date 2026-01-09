"""Comprehensive unit tests for order refund endpoint.

Tests all aspects of refund processing including validation,
Square API integration, inventory restoration, and email notifications.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException

from app.api.v1.orders import (
    RefundOrderRequest,
    RefundOrderResponse,
    refund_order,
    router,
)
from app.models.order import OrderStatus


# Helper constant for patch paths
PAYMENT_SERVICE_PATH = "app.services.square_payment.get_payment_service"
EMAIL_SERVICE_PATH = "app.services.email_service.get_email_service"
FULFILLMENT_SERVICE_PATH = "app.services.order_fulfillment.OrderFulfillmentService"


# ============================================
# Test Fixtures
# ============================================


@pytest.fixture
def mock_tenant():
    """Create mock tenant."""
    tenant = MagicMock()
    tenant.id = uuid4()
    return tenant


@pytest.fixture
def mock_db():
    """Create mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_order():
    """Create a standard mock order for testing."""
    order = MagicMock()
    order.id = uuid4()
    order.order_number = "MF-20251219-001"
    order.status = OrderStatus.PENDING
    order.payment_id = "square_payment_123"
    order.payment_provider = "square"
    order.payment_status = "COMPLETED"
    order.customer_email = "test@example.com"
    order.customer_name = "Test Customer"
    order.total = 50.00
    order.currency = "GBP"
    order.fulfilled_at = None
    order.internal_notes = None
    order.items = []
    return order


@pytest.fixture
def mock_fulfilled_order(mock_order):
    """Create a mock order that has been fulfilled."""
    mock_order.fulfilled_at = datetime.now(timezone.utc)
    return mock_order


@pytest.fixture
def mock_payment_service():
    """Create mock payment service."""
    service = MagicMock()
    service.refund_payment = MagicMock(
        return_value={
            "success": True,
            "refund_id": "refund_123",
            "status": "COMPLETED",
        }
    )
    return service


@pytest.fixture
def mock_email_service():
    """Create mock email service."""
    service = MagicMock()
    service.send_refund_confirmation = MagicMock(return_value=True)
    return service


@pytest.fixture
def mock_fulfillment_service():
    """Create mock fulfillment service."""
    service = MagicMock()
    revert_result = MagicMock()
    revert_result.success = True
    service.revert_inventory = AsyncMock(return_value=revert_result)
    return service


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/orders")
    return app


# ============================================
# Test RefundOrderRequest Schema
# ============================================


class TestRefundOrderRequestSchema:
    """Tests for RefundOrderRequest schema."""

    def test_default_values(self):
        """Test default values for refund request."""
        request = RefundOrderRequest()
        assert request.reason is None
        assert request.amount is None

    def test_with_reason(self):
        """Test request with reason."""
        request = RefundOrderRequest(reason="Customer requested refund")
        assert request.reason == "Customer requested refund"

    def test_with_partial_amount(self):
        """Test request with partial refund amount."""
        request = RefundOrderRequest(amount=25.50)
        assert request.amount == 25.50

    def test_with_all_fields(self):
        """Test request with all fields."""
        request = RefundOrderRequest(reason="Damaged item", amount=15.00)
        assert request.reason == "Damaged item"
        assert request.amount == 15.00


# ============================================
# Test RefundOrderResponse Schema
# ============================================


class TestRefundOrderResponseSchema:
    """Tests for RefundOrderResponse schema."""

    def test_minimal_response(self):
        """Test response with only message."""
        response = RefundOrderResponse(message="Order refunded")
        assert response.message == "Order refunded"
        assert response.refund_id is None
        assert response.refund_status is None
        assert response.refund_amount is None

    def test_full_response(self):
        """Test response with all fields."""
        response = RefundOrderResponse(
            message="Order refunded",
            refund_id="refund_123",
            refund_status="COMPLETED",
            refund_amount=50.00,
        )
        assert response.message == "Order refunded"
        assert response.refund_id == "refund_123"
        assert response.refund_status == "COMPLETED"
        assert response.refund_amount == 50.00


# ============================================
# Test Order Not Found
# ============================================


class TestRefundOrderNotFound:
    """Tests for order not found scenarios."""

    @pytest.mark.asyncio
    async def test_refund_nonexistent_order_returns_404(self, mock_db, mock_tenant):
        """Test that refunding a nonexistent order returns 404."""
        # Mock order not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with pytest.raises(HTTPException) as exc_info:
            await refund_order(uuid4(), request, mock_tenant, True, mock_db)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Order not found"


# ============================================
# Test Order Status Validation
# ============================================


class TestRefundOrderStatusValidation:
    """Tests for order status validation."""

    @pytest.mark.asyncio
    async def test_refund_already_refunded_order_returns_400(
        self, mock_db, mock_tenant, mock_order
    ):
        """Test that refunding an already refunded order returns 400."""
        mock_order.status = OrderStatus.REFUNDED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with pytest.raises(HTTPException) as exc_info:
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert exc_info.value.status_code == 400
        assert "already been refunded" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_refund_cancelled_order_returns_400(self, mock_db, mock_tenant, mock_order):
        """Test that refunding a cancelled order returns 400."""
        mock_order.status = OrderStatus.CANCELLED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with pytest.raises(HTTPException) as exc_info:
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert exc_info.value.status_code == 400
        assert "cancelled order" in exc_info.value.detail

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "status",
        [OrderStatus.PENDING, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED],
    )
    async def test_refund_allowed_for_valid_statuses(
        self,
        mock_db,
        mock_tenant,
        mock_order,
        mock_payment_service,
        mock_email_service,
        status,
    ):
        """Test that refund is allowed for various valid statuses."""
        mock_order.status = status

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            response = await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert response.refund_id == "refund_123"


# ============================================
# Test Payment Validation
# ============================================


class TestRefundPaymentValidation:
    """Tests for payment validation before refund."""

    @pytest.mark.asyncio
    async def test_refund_order_without_payment_id_returns_400(
        self, mock_db, mock_tenant, mock_order
    ):
        """Test that refunding an order without payment_id returns 400."""
        mock_order.payment_id = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with pytest.raises(HTTPException) as exc_info:
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert exc_info.value.status_code == 400
        assert "No payment ID" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_refund_non_square_payment_returns_400(self, mock_db, mock_tenant, mock_order):
        """Test that refunding a non-Square payment returns 400."""
        mock_order.payment_provider = "stripe"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with pytest.raises(HTTPException) as exc_info:
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert exc_info.value.status_code == 400
        assert "Square payments" in exc_info.value.detail


# ============================================
# Test Refund Amount Calculation
# ============================================


class TestRefundAmountCalculation:
    """Tests for refund amount calculation."""

    @pytest.mark.asyncio
    async def test_full_refund_uses_order_total(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that full refund uses order total."""
        mock_order.total = 75.00

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()  # No amount = full refund

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            response = await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        # Verify payment service was called with full amount in pence
        mock_payment_service.refund_payment.assert_called_once()
        call_kwargs = mock_payment_service.refund_payment.call_args[1]
        assert call_kwargs["amount"] == 7500  # 75.00 * 100

        assert response.refund_amount == 75.00

    @pytest.mark.asyncio
    async def test_partial_refund_uses_specified_amount(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that partial refund uses specified amount."""
        mock_order.total = 75.00

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest(amount=25.00)

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            response = await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        # Verify payment service was called with partial amount in pence
        mock_payment_service.refund_payment.assert_called_once()
        call_kwargs = mock_payment_service.refund_payment.call_args[1]
        assert call_kwargs["amount"] == 2500  # 25.00 * 100

        assert response.refund_amount == 25.00

    @pytest.mark.asyncio
    async def test_partial_refund_exceeding_total_returns_400(
        self, mock_db, mock_tenant, mock_order
    ):
        """Test that partial refund exceeding order total returns 400."""
        mock_order.total = 50.00

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest(amount=75.00)  # More than order total

        with pytest.raises(HTTPException) as exc_info:
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert exc_info.value.status_code == 400
        assert "exceeds order total" in exc_info.value.detail


# ============================================
# Test Square API Integration
# ============================================


class TestRefundSquareIntegration:
    """Tests for Square API integration during refund."""

    @pytest.mark.asyncio
    async def test_refund_calls_payment_service_correctly(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that refund calls payment service with correct parameters."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest(reason="Customer request")

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        mock_payment_service.refund_payment.assert_called_once()
        call_kwargs = mock_payment_service.refund_payment.call_args[1]
        assert call_kwargs["payment_id"] == "square_payment_123"
        assert call_kwargs["currency"] == "GBP"
        assert "Customer request" in call_kwargs["reason"]
        assert call_kwargs["idempotency_key"] == f"refund-{mock_order.order_number}"

    @pytest.mark.asyncio
    async def test_square_api_failure_returns_400(self, mock_db, mock_tenant, mock_order):
        """Test that Square API failure returns 400 with error details."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        # Mock payment service failure
        mock_payment_service = MagicMock()
        mock_payment_service.refund_payment.return_value = {
            "success": False,
            "error_code": "ALREADY_REFUNDED",
            "error_message": "Payment already refunded",
            "detail": "The payment has already been refunded",
        }

        request = RefundOrderRequest()

        with patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service):
            with pytest.raises(HTTPException) as exc_info:
                await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "ALREADY_REFUNDED"


# ============================================
# Test Inventory Restoration
# ============================================


class TestRefundInventoryRestoration:
    """Tests for inventory restoration during refund."""

    @pytest.mark.asyncio
    async def test_inventory_restored_for_fulfilled_order(
        self,
        mock_db,
        mock_tenant,
        mock_fulfilled_order,
        mock_payment_service,
        mock_email_service,
        mock_fulfillment_service,
    ):
        """Test that inventory is restored for fulfilled orders."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_fulfilled_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
            patch(
                FULFILLMENT_SERVICE_PATH,
                return_value=mock_fulfillment_service,
            ),
        ):
            response = await refund_order(
                mock_fulfilled_order.id, request, mock_tenant, True, mock_db
            )

        mock_fulfillment_service.revert_inventory.assert_awaited_once()
        assert "inventory restored" in response.message

    @pytest.mark.asyncio
    async def test_inventory_not_restored_for_unfulfilled_order(
        self,
        mock_db,
        mock_tenant,
        mock_order,
        mock_payment_service,
        mock_email_service,
    ):
        """Test that inventory is not restored for unfulfilled orders."""
        mock_order.fulfilled_at = None  # Not fulfilled

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            response = await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        # Message should not mention inventory restoration
        assert "inventory restored" not in response.message

    @pytest.mark.asyncio
    async def test_inventory_restoration_failure_logged_but_not_blocking(
        self,
        mock_db,
        mock_tenant,
        mock_fulfilled_order,
        mock_payment_service,
        mock_email_service,
    ):
        """Test that inventory restoration failure doesn't block refund."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_fulfilled_order
        mock_db.execute.return_value = mock_result

        # Mock fulfillment service failure
        mock_fulfillment_service = MagicMock()
        revert_result = MagicMock()
        revert_result.success = False
        mock_fulfillment_service.revert_inventory = AsyncMock(return_value=revert_result)

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
            patch(
                FULFILLMENT_SERVICE_PATH,
                return_value=mock_fulfillment_service,
            ),
        ):
            response = await refund_order(
                mock_fulfilled_order.id, request, mock_tenant, True, mock_db
            )

        # Refund should still succeed
        assert response.refund_id == "refund_123"
        # But message should not mention inventory restoration
        assert "inventory restored" not in response.message


# ============================================
# Test Order Status Update
# ============================================


class TestRefundOrderStatusUpdate:
    """Tests for order status update after refund."""

    @pytest.mark.asyncio
    async def test_order_status_updated_to_refunded(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that order status is updated to REFUNDED."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert mock_order.status == OrderStatus.REFUNDED
        assert mock_order.payment_status == "REFUNDED"

    @pytest.mark.asyncio
    async def test_refund_reason_added_to_internal_notes(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that refund reason is added to internal notes."""
        mock_order.internal_notes = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest(reason="Damaged during shipping")

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert "[Refunded]" in mock_order.internal_notes
        assert "Damaged during shipping" in mock_order.internal_notes

    @pytest.mark.asyncio
    async def test_refund_reason_appended_to_existing_notes(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that refund reason is appended to existing internal notes."""
        mock_order.internal_notes = "Previous note"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest(reason="Item not as described")

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert "Previous note" in mock_order.internal_notes
        assert "[Refunded]" in mock_order.internal_notes
        assert "Item not as described" in mock_order.internal_notes


# ============================================
# Test Email Notification
# ============================================


class TestRefundEmailNotification:
    """Tests for email notification after refund."""

    @pytest.mark.asyncio
    async def test_refund_confirmation_email_sent(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that refund confirmation email is sent."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest(reason="Customer request")

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        mock_email_service.send_refund_confirmation.assert_called_once()
        call_kwargs = mock_email_service.send_refund_confirmation.call_args[1]
        assert call_kwargs["to_email"] == "test@example.com"
        assert call_kwargs["customer_name"] == "Test Customer"
        assert call_kwargs["order_number"] == "MF-20251219-001"
        assert call_kwargs["reason"] == "Customer request"

    @pytest.mark.asyncio
    async def test_email_failure_does_not_block_refund(
        self, mock_db, mock_tenant, mock_order, mock_payment_service
    ):
        """Test that email failure doesn't block refund success."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        # Mock email service failure
        mock_email_service = MagicMock()
        mock_email_service.send_refund_confirmation.side_effect = Exception("SMTP error")

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            # Should not raise despite email failure
            response = await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        # Refund should still succeed
        assert response.refund_id == "refund_123"


# ============================================
# Test Response Message
# ============================================


class TestRefundResponseMessage:
    """Tests for refund response message formatting."""

    @pytest.mark.asyncio
    async def test_response_message_includes_order_number(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that response message includes order number."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            response = await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert mock_order.order_number in response.message

    @pytest.mark.asyncio
    async def test_response_message_includes_refund_amount(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that response message includes refund amount."""
        mock_order.total = 35.50

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            response = await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        assert "35.50" in response.message


# ============================================
# Test Database Commit
# ============================================


class TestRefundDatabaseCommit:
    """Tests for database commit during refund."""

    @pytest.mark.asyncio
    async def test_database_committed_after_refund(
        self, mock_db, mock_tenant, mock_order, mock_payment_service, mock_email_service
    ):
        """Test that database is committed after successful refund."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_order
        mock_db.execute.return_value = mock_result

        request = RefundOrderRequest()

        with (
            patch(PAYMENT_SERVICE_PATH, return_value=mock_payment_service),
            patch(EMAIL_SERVICE_PATH, return_value=mock_email_service),
        ):
            await refund_order(mock_order.id, request, mock_tenant, True, mock_db)

        mock_db.commit.assert_awaited_once()
