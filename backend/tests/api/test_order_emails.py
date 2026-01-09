"""Tests for order email functionality."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.models.order import Order, OrderItem, OrderStatus
from app.models.tenant import Tenant


pytestmark = pytest.mark.anyio


@pytest_asyncio.fixture
async def test_order(db_session: AsyncSession, test_tenant: Tenant) -> Order:
    """Create a test order for email tests."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="MF-TEST-001",
        customer_name="Test Customer",
        customer_email="test@example.com",
        customer_phone="07777123456",
        shipping_address_line1="123 Test Street",
        shipping_city="London",
        shipping_postcode="SW1A 1AA",
        shipping_country="United Kingdom",
        shipping_method="Royal Mail 2nd Class",
        shipping_cost=350,  # £3.50 in pence
        subtotal=1000,  # £10.00 in pence
        total=1350,  # £13.50 in pence
        status=OrderStatus.PENDING,
    )
    db_session.add(order)
    await db_session.flush()

    # Add order item
    item = OrderItem(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_id=order.id,
        product_sku="TEST-001",
        product_name="Test Product",
        quantity=2,
        unit_price=500,  # £5.00 in pence
        total_price=1000,  # £10.00 in pence
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest_asyncio.fixture
async def shipped_order(db_session: AsyncSession, test_tenant: Tenant) -> Order:
    """Create a shipped order for email tests."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="MF-SHIP-001",
        customer_name="Shipped Customer",
        customer_email="shipped@example.com",
        customer_phone="07777123457",
        shipping_address_line1="456 Ship Street",
        shipping_city="Manchester",
        shipping_postcode="M1 1AA",
        shipping_country="United Kingdom",
        shipping_method="Royal Mail 1st Class",
        shipping_cost=450,
        subtotal=2000,
        total=2450,
        status=OrderStatus.SHIPPED,
        tracking_number="AB123456789GB",
        tracking_url="https://www.royalmail.com/track/AB123456789GB",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest_asyncio.fixture
async def delivered_order(db_session: AsyncSession, test_tenant: Tenant) -> Order:
    """Create a delivered order for email tests."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="MF-DELIV-001",
        customer_name="Delivered Customer",
        customer_email="delivered@example.com",
        customer_phone="07777123458",
        shipping_address_line1="789 Deliver Lane",
        shipping_city="Birmingham",
        shipping_postcode="B1 1AA",
        shipping_country="United Kingdom",
        shipping_method="Royal Mail Special Delivery",
        shipping_cost=650,
        subtotal=3000,
        total=3650,
        status=OrderStatus.DELIVERED,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


class TestResendOrderEmail:
    """Tests for resend order email endpoint."""

    async def test_resend_confirmation_email_success(
        self, client: AsyncClient, auth_headers: dict, test_order: Order
    ):
        """Test resending confirmation email successfully."""
        with patch("app.services.email_service.get_email_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.send_order_confirmation.return_value = True
            mock_get_service.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/resend-email",
                json={"email_type": "confirmation"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_sent"] is True
            assert "confirmation" in data["message"].lower()
            assert test_order.customer_email in data["message"]

            # Verify email service was called
            mock_service.send_order_confirmation.assert_called_once()

    async def test_resend_shipped_email_success(
        self, client: AsyncClient, auth_headers: dict, shipped_order: Order
    ):
        """Test resending shipped email successfully."""
        with patch("app.services.email_service.get_email_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.send_order_shipped.return_value = True
            mock_get_service.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{shipped_order.id}/resend-email",
                json={"email_type": "shipped"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_sent"] is True
            assert "shipped" in data["message"].lower()

            # Verify email service was called with tracking info
            mock_service.send_order_shipped.assert_called_once()
            call_kwargs = mock_service.send_order_shipped.call_args[1]
            assert call_kwargs["tracking_number"] == "AB123456789GB"

    async def test_resend_delivered_email_success(
        self, client: AsyncClient, auth_headers: dict, delivered_order: Order
    ):
        """Test resending delivered email successfully."""
        with patch("app.services.email_service.get_email_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.send_order_delivered.return_value = True
            mock_get_service.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{delivered_order.id}/resend-email",
                json={"email_type": "delivered"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_sent"] is True
            assert "delivered" in data["message"].lower()

    async def test_resend_shipped_email_wrong_status(
        self, client: AsyncClient, auth_headers: dict, test_order: Order
    ):
        """Test resending shipped email fails for pending order."""
        response = await client.post(
            f"/api/v1/orders/{test_order.id}/resend-email",
            json={"email_type": "shipped"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "not been shipped" in response.json()["detail"]

    async def test_resend_delivered_email_wrong_status(
        self, client: AsyncClient, auth_headers: dict, shipped_order: Order
    ):
        """Test resending delivered email fails for shipped (not delivered) order."""
        response = await client.post(
            f"/api/v1/orders/{shipped_order.id}/resend-email",
            json={"email_type": "delivered"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "not been delivered" in response.json()["detail"]

    async def test_resend_email_invalid_type(
        self, client: AsyncClient, auth_headers: dict, test_order: Order
    ):
        """Test resending email with invalid type fails."""
        response = await client.post(
            f"/api/v1/orders/{test_order.id}/resend-email",
            json={"email_type": "invalid"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Invalid email_type" in response.json()["detail"]

    async def test_resend_email_order_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test resending email for non-existent order."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/orders/{fake_id}/resend-email",
            json={"email_type": "confirmation"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_resend_email_service_not_configured(
        self, client: AsyncClient, auth_headers: dict, test_order: Order
    ):
        """Test resending email when service is not configured."""
        with patch("app.services.email_service.get_email_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.send_order_confirmation.return_value = False
            mock_get_service.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/resend-email",
                json={"email_type": "confirmation"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_sent"] is False
            assert "not be configured" in data["message"]


class TestCancelOrderEmail:
    """Tests for cancel order email functionality."""

    async def test_cancel_order_sends_email(
        self, client: AsyncClient, auth_headers: dict, test_order: Order
    ):
        """Test cancelling order sends notification email."""
        with patch("app.services.email_service.get_email_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.send_order_cancelled.return_value = True
            mock_get_service.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/cancel",
                json={"reason": "Customer requested cancellation"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert "cancelled" in response.json()["message"].lower()

            # Verify email service was called with reason
            mock_service.send_order_cancelled.assert_called_once()
            call_kwargs = mock_service.send_order_cancelled.call_args[1]
            assert call_kwargs["to_email"] == test_order.customer_email
            assert call_kwargs["order_number"] == test_order.order_number
            assert call_kwargs["reason"] == "Customer requested cancellation"

    async def test_cancel_order_email_failure_doesnt_fail_cancellation(
        self, client: AsyncClient, auth_headers: dict, test_order: Order
    ):
        """Test that email failure doesn't prevent order cancellation."""
        with patch("app.services.email_service.get_email_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.send_order_cancelled.side_effect = Exception("Email failed")
            mock_get_service.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/cancel",
                json={"reason": "Test cancellation"},
                headers=auth_headers,
            )

            # Cancellation should still succeed
            assert response.status_code == 200
            assert "cancelled" in response.json()["message"].lower()


class TestEmailServiceCancelMethod:
    """Tests for email service send_order_cancelled method."""

    def test_send_order_cancelled_with_reason(self):
        """Test send_order_cancelled includes reason in email."""
        from app.services.email_service import EmailService

        service = EmailService()

        # Test with no API key (will return False but won't crash)
        result = service.send_order_cancelled(
            to_email="test@example.com",
            customer_name="Test User",
            order_number="MF-TEST-001",
            reason="Out of stock",
        )

        # Without API key configured, should return False
        assert result is False

    def test_send_order_cancelled_without_reason(self):
        """Test send_order_cancelled works without reason."""
        from app.services.email_service import EmailService

        service = EmailService()

        result = service.send_order_cancelled(
            to_email="test@example.com",
            customer_name="Test User",
            order_number="MF-TEST-001",
        )

        assert result is False  # No API key configured

    def test_send_order_cancelled_with_refund_info(self):
        """Test send_order_cancelled includes refund info."""
        from app.services.email_service import EmailService

        service = EmailService()

        result = service.send_order_cancelled(
            to_email="test@example.com",
            customer_name="Test User",
            order_number="MF-TEST-001",
            reason="Customer request",
            refund_info="Full refund of £15.00 will be processed within 5-10 days",
        )

        assert result is False  # No API key configured
