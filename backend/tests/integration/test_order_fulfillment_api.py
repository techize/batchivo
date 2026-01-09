"""
Integration tests for order fulfillment API endpoints.
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.tenant import Tenant


@pytest.fixture
async def test_product_for_api(db_session: AsyncSession, test_tenant: Tenant) -> Product:
    """Create a test product with stock for API tests."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="API-TEST-001",
        name="API Test Product",
        description="Test product for API tests",
        units_in_stock=20,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_order_for_api(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_product_for_api: Product,
) -> Order:
    """Create a test order for API tests."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="API-ORDER-001",
        status=OrderStatus.PENDING,
        customer_email="api-test@example.com",
        customer_name="API Test Customer",
        shipping_address_line1="456 API St",
        shipping_city="API City",
        shipping_postcode="AP1 1TP",
        shipping_country="United Kingdom",
        shipping_method="API Shipping",
        shipping_cost=Decimal("3.50"),
        subtotal=Decimal("40.00"),
        total=Decimal("43.50"),
        currency="GBP",
        payment_provider="test",
        payment_status="completed",
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_id=order.id,
        product_id=test_product_for_api.id,
        product_sku=test_product_for_api.sku,
        product_name=test_product_for_api.name,
        quantity=5,
        unit_price=Decimal("8.00"),
        total_price=Decimal("40.00"),
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(order)
    return order


class TestOrderFulfillmentAPI:
    """Tests for order fulfillment API endpoints."""

    @pytest.mark.asyncio
    async def test_fulfill_order_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
        test_product_for_api: Product,
    ):
        """Test fulfilling an order via API."""
        response = await client.post(f"/api/v1/orders/{test_order_for_api.id}/fulfill")

        assert response.status_code == 200
        data = response.json()
        assert "fulfilled" in data["message"].lower()

        # Check inventory was deducted
        await db_session.refresh(test_product_for_api)
        assert test_product_for_api.units_in_stock == 15  # 20 - 5

    @pytest.mark.asyncio
    async def test_fulfill_order_already_fulfilled(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
    ):
        """Test fulfilling an already fulfilled order returns 400."""
        # First fulfill
        response = await client.post(f"/api/v1/orders/{test_order_for_api.id}/fulfill")
        assert response.status_code == 200

        # Try to fulfill again
        response = await client.post(f"/api/v1/orders/{test_order_for_api.id}/fulfill")
        assert response.status_code == 400
        assert "already been fulfilled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_fulfill_order_insufficient_inventory(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test fulfilling order with insufficient inventory returns 400."""
        # Create product with low stock
        product = Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="LOW-STOCK-API",
            name="Low Stock API Product",
            units_in_stock=1,
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()

        # Create order needing more than available
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="INSUFFICIENT-001",
            status=OrderStatus.PENDING,
            customer_email="test@example.com",
            customer_name="Test",
            shipping_address_line1="Test",
            shipping_city="Test",
            shipping_postcode="TE1 1ST",
            shipping_country="UK",
            shipping_method="Test",
            shipping_cost=Decimal("0"),
            subtotal=Decimal("50.00"),
            total=Decimal("50.00"),
            currency="GBP",
            payment_provider="test",
            payment_status="completed",
        )
        db_session.add(order)
        await db_session.flush()

        item = OrderItem(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_id=order.id,
            product_id=product.id,
            product_sku=product.sku,
            product_name=product.name,
            quantity=10,  # Need 10 but only 1 in stock
            unit_price=Decimal("5.00"),
            total_price=Decimal("50.00"),
        )
        db_session.add(item)
        await db_session.commit()

        response = await client.post(f"/api/v1/orders/{order.id}/fulfill")
        assert response.status_code == 400
        assert "insufficient inventory" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_fulfill_order_not_found(
        self,
        client: AsyncClient,
    ):
        """Test fulfilling non-existent order returns 404."""
        fake_id = uuid4()
        response = await client.post(f"/api/v1/orders/{fake_id}/fulfill")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_fulfill_order_wrong_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test fulfilling shipped order returns 400."""
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="SHIPPED-001",
            status=OrderStatus.SHIPPED,  # Already shipped
            customer_email="test@example.com",
            customer_name="Test",
            shipping_address_line1="Test",
            shipping_city="Test",
            shipping_postcode="TE1 1ST",
            shipping_country="UK",
            shipping_method="Test",
            shipping_cost=Decimal("0"),
            subtotal=Decimal("10.00"),
            total=Decimal("10.00"),
            currency="GBP",
            payment_provider="test",
            payment_status="completed",
        )
        db_session.add(order)
        await db_session.commit()

        response = await client.post(f"/api/v1/orders/{order.id}/fulfill")
        assert response.status_code == 400
        assert "cannot fulfill order with status" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_ship_order_auto_fulfills(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
        test_product_for_api: Product,
    ):
        """Test shipping an order auto-fulfills if not fulfilled."""
        response = await client.post(
            f"/api/v1/orders/{test_order_for_api.id}/ship",
            json={"tracking_number": "TRACK123"},
        )

        assert response.status_code == 200

        # Check inventory was deducted (auto-fulfilled)
        await db_session.refresh(test_product_for_api)
        assert test_product_for_api.units_in_stock == 15  # 20 - 5

        # Check order status
        await db_session.refresh(test_order_for_api)
        assert test_order_for_api.status == OrderStatus.SHIPPED
        assert test_order_for_api.fulfilled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_order_restores_inventory(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
        test_product_for_api: Product,
    ):
        """Test cancelling fulfilled order restores inventory."""
        # First fulfill
        await client.post(f"/api/v1/orders/{test_order_for_api.id}/fulfill")
        await db_session.refresh(test_product_for_api)
        assert test_product_for_api.units_in_stock == 15

        # Cancel
        response = await client.post(
            f"/api/v1/orders/{test_order_for_api.id}/cancel",
            json={"reason": "Test cancellation"},
        )

        assert response.status_code == 200
        assert "inventory restored" in response.json()["message"].lower()

        # Check inventory was restored
        await db_session.refresh(test_product_for_api)
        assert test_product_for_api.units_in_stock == 20

    @pytest.mark.asyncio
    async def test_cancel_order_unfulfilled_no_restore(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
        test_product_for_api: Product,
    ):
        """Test cancelling unfulfilled order doesn't mention inventory."""
        initial_stock = test_product_for_api.units_in_stock

        response = await client.post(
            f"/api/v1/orders/{test_order_for_api.id}/cancel",
            json={"reason": "Changed mind"},
        )

        assert response.status_code == 200
        assert "inventory restored" not in response.json()["message"].lower()

        # Stock unchanged
        await db_session.refresh(test_product_for_api)
        assert test_product_for_api.units_in_stock == initial_stock


class TestOrderStatusEmails:
    """Tests for order status email notifications."""

    @pytest.mark.asyncio
    async def test_ship_order_sends_email(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
        test_product_for_api: Product,
    ):
        """Test shipping an order sends shipped notification email."""
        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_email_service = MagicMock()
            mock_email_service.send_order_shipped.return_value = True
            mock_get_email.return_value = mock_email_service

            response = await client.post(
                f"/api/v1/orders/{test_order_for_api.id}/ship",
                json={
                    "tracking_number": "TRACK123",
                    "tracking_url": "https://track.example.com/TRACK123",
                },
            )

            assert response.status_code == 200

            # Verify email was called with correct params
            mock_email_service.send_order_shipped.assert_called_once_with(
                to_email=test_order_for_api.customer_email,
                customer_name=test_order_for_api.customer_name,
                order_number=test_order_for_api.order_number,
                tracking_number="TRACK123",
                tracking_url="https://track.example.com/TRACK123",
                shipping_method=test_order_for_api.shipping_method,
            )

            # Check email tracking fields were updated
            await db_session.refresh(test_order_for_api)
            assert test_order_for_api.shipped_email_sent is True
            assert test_order_for_api.shipped_email_sent_at is not None

    @pytest.mark.asyncio
    async def test_ship_order_email_failure_does_not_block(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
        test_product_for_api: Product,
    ):
        """Test shipping still succeeds even if email fails."""
        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_email_service = MagicMock()
            mock_email_service.send_order_shipped.return_value = False
            mock_get_email.return_value = mock_email_service

            response = await client.post(
                f"/api/v1/orders/{test_order_for_api.id}/ship",
                json={"tracking_number": "TRACK123"},
            )

            assert response.status_code == 200

            # Order should still be shipped
            await db_session.refresh(test_order_for_api)
            assert test_order_for_api.status == OrderStatus.SHIPPED
            # But email tracking not updated
            assert test_order_for_api.shipped_email_sent is False

    @pytest.mark.asyncio
    async def test_ship_order_without_tracking(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
        test_product_for_api: Product,
    ):
        """Test shipping an order without tracking info."""
        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_email_service = MagicMock()
            mock_email_service.send_order_shipped.return_value = True
            mock_get_email.return_value = mock_email_service

            response = await client.post(
                f"/api/v1/orders/{test_order_for_api.id}/ship",
                json={},
            )

            assert response.status_code == 200

            # Email called without tracking
            mock_email_service.send_order_shipped.assert_called_once_with(
                to_email=test_order_for_api.customer_email,
                customer_name=test_order_for_api.customer_name,
                order_number=test_order_for_api.order_number,
                tracking_number=None,
                tracking_url=None,
                shipping_method=test_order_for_api.shipping_method,
            )

    @pytest.mark.asyncio
    async def test_deliver_order_sends_email(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test marking order as delivered sends delivered notification email."""
        # Create a shipped order
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="DELIVER-TEST-001",
            status=OrderStatus.SHIPPED,  # Already shipped
            shipped_at=datetime.now(timezone.utc),
            customer_email="deliver@example.com",
            customer_name="Deliver Test Customer",
            shipping_address_line1="789 Deliver Ave",
            shipping_city="Deliver City",
            shipping_postcode="DE1 1VR",
            shipping_country="United Kingdom",
            shipping_method="Royal Mail",
            shipping_cost=Decimal("4.00"),
            subtotal=Decimal("30.00"),
            total=Decimal("34.00"),
            currency="GBP",
            payment_provider="test",
            payment_status="completed",
        )
        db_session.add(order)
        await db_session.commit()

        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_email_service = MagicMock()
            mock_email_service.send_order_delivered.return_value = True
            mock_get_email.return_value = mock_email_service

            response = await client.post(f"/api/v1/orders/{order.id}/deliver")

            assert response.status_code == 200

            # Verify email was called
            mock_email_service.send_order_delivered.assert_called_once_with(
                to_email="deliver@example.com",
                customer_name="Deliver Test Customer",
                order_number="DELIVER-TEST-001",
            )

            # Check email tracking fields
            await db_session.refresh(order)
            assert order.delivered_email_sent is True
            assert order.delivered_email_sent_at is not None
            assert order.status == OrderStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_deliver_order_email_failure_does_not_block(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test delivery still succeeds even if email fails."""
        # Create a shipped order
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="DELIVER-FAIL-001",
            status=OrderStatus.SHIPPED,
            shipped_at=datetime.now(timezone.utc),
            customer_email="fail@example.com",
            customer_name="Fail Test",
            shipping_address_line1="Test",
            shipping_city="Test",
            shipping_postcode="TE1 1ST",
            shipping_country="UK",
            shipping_method="Test",
            shipping_cost=Decimal("0"),
            subtotal=Decimal("10.00"),
            total=Decimal("10.00"),
            currency="GBP",
            payment_provider="test",
            payment_status="completed",
        )
        db_session.add(order)
        await db_session.commit()

        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_email_service = MagicMock()
            mock_email_service.send_order_delivered.return_value = False
            mock_get_email.return_value = mock_email_service

            response = await client.post(f"/api/v1/orders/{order.id}/deliver")

            assert response.status_code == 200

            # Order should still be delivered
            await db_session.refresh(order)
            assert order.status == OrderStatus.DELIVERED
            # But email tracking not updated
            assert order.delivered_email_sent is False

    @pytest.mark.asyncio
    async def test_deliver_order_not_shipped_returns_400(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order_for_api: Order,
    ):
        """Test cannot deliver an order that hasn't been shipped."""
        response = await client.post(f"/api/v1/orders/{test_order_for_api.id}/deliver")

        assert response.status_code == 400
        assert "not shipped" in response.json()["detail"].lower()
