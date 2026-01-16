"""
Integration tests for Orders API endpoints.

Tests cover:
- GET /orders (list with filtering)
- GET /orders/counts (status counts)
- GET /orders/{id} (get single order)
- PATCH /orders/{id} (update order)
- POST /orders/{id}/refund (refund order)
- POST /orders/{id}/resend-email (resend notification email)
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.tenant import Tenant


# ============================================
# Fixtures
# ============================================


@pytest.fixture
async def test_product_for_orders(db_session: AsyncSession, test_tenant: Tenant) -> Product:
    """Create a test product for order tests."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="ORDERS-TEST-001",
        name="Orders Test Product",
        description="Product for orders API tests",
        units_in_stock=100,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_order(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_product_for_orders: Product,
) -> Order:
    """Create a single test order."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="ORD-001",
        status=OrderStatus.PENDING,
        customer_email="customer@example.com",
        customer_name="John Doe",
        customer_phone="+44 1234 567890",
        shipping_address_line1="123 Test Street",
        shipping_address_line2="Apt 4",
        shipping_city="London",
        shipping_county="Greater London",
        shipping_postcode="SW1A 1AA",
        shipping_country="United Kingdom",
        shipping_method="Royal Mail Tracked",
        shipping_cost=Decimal("4.99"),
        subtotal=Decimal("29.99"),
        total=Decimal("34.98"),
        currency="GBP",
        payment_provider="square",
        payment_id="sq_pay_12345",
        payment_status="completed",
        customer_notes="Please leave at door",
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_id=order.id,
        product_id=test_product_for_orders.id,
        product_sku=test_product_for_orders.sku,
        product_name=test_product_for_orders.name,
        quantity=2,
        unit_price=Decimal("14.995"),
        total_price=Decimal("29.99"),
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest.fixture
async def multiple_orders(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_product_for_orders: Product,
) -> list[Order]:
    """Create multiple test orders with different statuses."""
    orders = []
    statuses = [
        (OrderStatus.PENDING, "pending@example.com", "Pending Customer"),
        (OrderStatus.PROCESSING, "processing@example.com", "Processing Customer"),
        (OrderStatus.SHIPPED, "shipped@example.com", "Shipped Customer"),
        (OrderStatus.DELIVERED, "delivered@example.com", "Delivered Customer"),
        (OrderStatus.CANCELLED, "cancelled@example.com", "Cancelled Customer"),
    ]

    for i, (status, email, name) in enumerate(statuses):
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number=f"MULTI-{i + 1:03d}",
            status=status,
            customer_email=email,
            customer_name=name,
            shipping_address_line1=f"{i + 1} Test Avenue",
            shipping_city="Manchester",
            shipping_postcode=f"M{i + 1} {i + 1}AB",
            shipping_country="United Kingdom",
            shipping_method="Standard Delivery",
            shipping_cost=Decimal("3.99"),
            subtotal=Decimal("19.99"),
            total=Decimal("23.98"),
            currency="GBP",
            payment_provider="square",
            payment_status="completed",
            created_at=datetime.now(timezone.utc) - timedelta(days=i),
        )
        db_session.add(order)
        await db_session.flush()

        item = OrderItem(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_id=order.id,
            product_id=test_product_for_orders.id,
            product_sku=test_product_for_orders.sku,
            product_name=test_product_for_orders.name,
            quantity=1,
            unit_price=Decimal("19.99"),
            total_price=Decimal("19.99"),
        )
        db_session.add(item)
        orders.append(order)

    await db_session.commit()
    for order in orders:
        await db_session.refresh(order)
    return orders


# ============================================
# GET /orders Tests
# ============================================


class TestListOrders:
    """Tests for GET /orders endpoint."""

    @pytest.mark.asyncio
    async def test_list_orders_empty(self, client: AsyncClient):
        """Test listing orders when none exist."""
        response = await client.get("/api/v1/orders")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_orders_with_data(self, client: AsyncClient, multiple_orders: list[Order]):
        """Test listing orders returns all orders."""
        response = await client.get("/api/v1/orders")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_list_orders_filter_by_status(
        self, client: AsyncClient, multiple_orders: list[Order]
    ):
        """Test filtering orders by status."""
        response = await client.get("/api/v1/orders?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_orders_filter_by_shipped_status(
        self, client: AsyncClient, multiple_orders: list[Order]
    ):
        """Test filtering orders by shipped status."""
        response = await client.get("/api/v1/orders?status=shipped")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["status"] == "shipped"

    @pytest.mark.asyncio
    async def test_list_orders_search_by_order_number(
        self, client: AsyncClient, multiple_orders: list[Order]
    ):
        """Test searching orders by order number."""
        response = await client.get("/api/v1/orders?search=MULTI-001")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["order_number"] == "MULTI-001"

    @pytest.mark.asyncio
    async def test_list_orders_search_by_customer_name(
        self, client: AsyncClient, multiple_orders: list[Order]
    ):
        """Test searching orders by customer name."""
        response = await client.get("/api/v1/orders?search=Shipped%20Customer")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["customer_name"] == "Shipped Customer"

    @pytest.mark.asyncio
    async def test_list_orders_search_by_email(
        self, client: AsyncClient, multiple_orders: list[Order]
    ):
        """Test searching orders by customer email."""
        response = await client.get("/api/v1/orders?search=delivered@example.com")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["customer_email"] == "delivered@example.com"

    @pytest.mark.asyncio
    async def test_list_orders_search_case_insensitive(
        self, client: AsyncClient, multiple_orders: list[Order]
    ):
        """Test search is case insensitive."""
        response = await client.get("/api/v1/orders?search=PENDING@EXAMPLE.COM")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    @pytest.mark.asyncio
    async def test_list_orders_pagination(self, client: AsyncClient, multiple_orders: list[Order]):
        """Test pagination works correctly."""
        # First page
        response = await client.get("/api/v1/orders?page=1&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["limit"] == 2
        assert data["has_more"] is True

        # Second page
        response = await client.get("/api/v1/orders?page=2&limit=2")
        data = response.json()
        assert len(data["data"]) == 2
        assert data["has_more"] is True

        # Third page (last)
        response = await client.get("/api/v1/orders?page=3&limit=2")
        data = response.json()
        assert len(data["data"]) == 1
        assert data["has_more"] is False

    @pytest.mark.asyncio
    async def test_list_orders_includes_items(self, client: AsyncClient, test_order: Order):
        """Test orders include their items."""
        response = await client.get("/api/v1/orders")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert len(data["data"][0]["items"]) == 1
        assert data["data"][0]["items"][0]["product_sku"] == "ORDERS-TEST-001"

    @pytest.mark.asyncio
    async def test_list_orders_date_range_filter(
        self, client: AsyncClient, multiple_orders: list[Order]
    ):
        """Test filtering orders by date range."""
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        response = await client.get(f"/api/v1/orders?date_from={yesterday}&date_to={today}")
        assert response.status_code == 200
        data = response.json()
        # Should include orders from today and yesterday
        assert len(data["data"]) >= 1


# ============================================
# GET /orders/counts Tests
# ============================================


class TestOrderCounts:
    """Tests for GET /orders/counts endpoint."""

    @pytest.mark.asyncio
    async def test_order_counts_empty(self, client: AsyncClient):
        """Test order counts when no orders exist."""
        response = await client.get("/api/v1/orders/counts")
        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 0
        assert data["processing"] == 0
        assert data["shipped"] == 0
        assert data["delivered"] == 0
        assert data["cancelled"] == 0
        assert data["refunded"] == 0
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_order_counts_with_orders(
        self, client: AsyncClient, multiple_orders: list[Order]
    ):
        """Test order counts returns correct counts per status."""
        response = await client.get("/api/v1/orders/counts")
        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 1
        assert data["processing"] == 1
        assert data["shipped"] == 1
        assert data["delivered"] == 1
        assert data["cancelled"] == 1
        assert data["refunded"] == 0
        assert data["total"] == 5


# ============================================
# GET /orders/{id} Tests
# ============================================


class TestGetOrder:
    """Tests for GET /orders/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_order_success(self, client: AsyncClient, test_order: Order):
        """Test getting a single order by ID."""
        response = await client.get(f"/api/v1/orders/{test_order.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_order.id)
        assert data["order_number"] == "ORD-001"
        assert data["customer_email"] == "customer@example.com"
        assert data["customer_name"] == "John Doe"
        assert data["shipping_city"] == "London"
        assert float(data["total"]) == pytest.approx(34.98, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_order_includes_items(self, client: AsyncClient, test_order: Order):
        """Test order response includes items."""
        response = await client.get(f"/api/v1/orders/{test_order.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["product_sku"] == "ORDERS-TEST-001"
        assert item["quantity"] == 2

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, client: AsyncClient):
        """Test getting non-existent order returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/orders/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_order_wrong_tenant(self, client: AsyncClient, db_session: AsyncSession):
        """Test cannot access order from different tenant."""
        # Create order for a different tenant
        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant",
            slug="other-tenant",
        )
        db_session.add(other_tenant)
        await db_session.flush()

        other_order = Order(
            id=uuid4(),
            tenant_id=other_tenant.id,
            order_number="OTHER-001",
            status=OrderStatus.PENDING,
            customer_email="other@example.com",
            customer_name="Other Customer",
            shipping_address_line1="Other Street",
            shipping_city="Other City",
            shipping_postcode="OT1 1ER",
            shipping_country="UK",
            shipping_method="Other",
            shipping_cost=Decimal("0"),
            subtotal=Decimal("10"),
            total=Decimal("10"),
            currency="GBP",
            payment_provider="test",
            payment_status="completed",
        )
        db_session.add(other_order)
        await db_session.commit()

        # Try to access from test tenant
        response = await client.get(f"/api/v1/orders/{other_order.id}")
        assert response.status_code == 404


# ============================================
# PATCH /orders/{id} Tests
# ============================================


class TestUpdateOrder:
    """Tests for PATCH /orders/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_order_status(self, client: AsyncClient, test_order: Order):
        """Test updating order status."""
        response = await client.patch(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "processing"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"

    @pytest.mark.asyncio
    async def test_update_order_tracking(self, client: AsyncClient, test_order: Order):
        """Test updating tracking information."""
        response = await client.patch(
            f"/api/v1/orders/{test_order.id}",
            json={
                "tracking_number": "RM123456789GB",
                "tracking_url": "https://www.royalmail.com/track/RM123456789GB",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_number"] == "RM123456789GB"
        assert "royalmail.com" in data["tracking_url"]

    @pytest.mark.asyncio
    async def test_update_order_internal_notes(self, client: AsyncClient, test_order: Order):
        """Test updating internal notes."""
        response = await client.patch(
            f"/api/v1/orders/{test_order.id}",
            json={"internal_notes": "Customer called to check on order"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["internal_notes"] == "Customer called to check on order"

    @pytest.mark.asyncio
    async def test_update_order_multiple_fields(self, client: AsyncClient, test_order: Order):
        """Test updating multiple fields at once."""
        response = await client.patch(
            f"/api/v1/orders/{test_order.id}",
            json={
                "status": "processing",
                "internal_notes": "Being prepared",
                "tracking_number": "TRACK123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["internal_notes"] == "Being prepared"
        assert data["tracking_number"] == "TRACK123"

    @pytest.mark.asyncio
    async def test_update_order_invalid_status(self, client: AsyncClient, test_order: Order):
        """Test updating with invalid status returns 400."""
        response = await client.patch(
            f"/api/v1/orders/{test_order.id}",
            json={"status": "invalid_status"},
        )
        assert response.status_code == 400
        assert "invalid status" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_order_not_found(self, client: AsyncClient):
        """Test updating non-existent order returns 404."""
        fake_id = uuid4()
        response = await client.patch(
            f"/api/v1/orders/{fake_id}",
            json={"status": "processing"},
        )
        assert response.status_code == 404


# ============================================
# POST /orders/{id}/refund Tests
# ============================================


class TestRefundOrder:
    """Tests for POST /orders/{id}/refund endpoint."""

    @pytest.mark.asyncio
    async def test_refund_order_success(
        self, client: AsyncClient, db_session: AsyncSession, test_order: Order
    ):
        """Test successful full refund."""
        with patch("app.services.square_payment.get_payment_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.refund_payment.return_value = {
                "success": True,
                "refund_id": "refund_123",
                "status": "COMPLETED",
            }
            mock_get_service.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/refund",
                json={"reason": "Customer requested refund"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "refunded" in data["message"].lower()
            assert data["refund_id"] == "refund_123"
            assert data["refund_status"] == "COMPLETED"
            assert data["refund_amount"] == pytest.approx(34.98, rel=0.01)

    @pytest.mark.asyncio
    async def test_refund_order_partial(self, client: AsyncClient, test_order: Order):
        """Test partial refund with specific amount."""
        with patch("app.services.square_payment.get_payment_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.refund_payment.return_value = {
                "success": True,
                "refund_id": "refund_456",
                "status": "COMPLETED",
            }
            mock_get_service.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/refund",
                json={"reason": "Partial refund for damaged item", "amount": 10.00},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["refund_amount"] == 10.00

    @pytest.mark.asyncio
    async def test_refund_order_amount_exceeds_total(self, client: AsyncClient, test_order: Order):
        """Test refund amount exceeding order total returns 400."""
        response = await client.post(
            f"/api/v1/orders/{test_order.id}/refund",
            json={"amount": 1000.00},
        )
        assert response.status_code == 400
        assert "exceeds" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refund_already_refunded_order(
        self, client: AsyncClient, db_session: AsyncSession, test_order: Order
    ):
        """Test cannot refund already refunded order."""
        test_order.status = OrderStatus.REFUNDED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/orders/{test_order.id}/refund",
            json={},
        )
        assert response.status_code == 400
        assert "already been refunded" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refund_cancelled_order(
        self, client: AsyncClient, db_session: AsyncSession, test_order: Order
    ):
        """Test cannot refund cancelled order."""
        test_order.status = OrderStatus.CANCELLED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/orders/{test_order.id}/refund",
            json={},
        )
        assert response.status_code == 400
        assert "cancelled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refund_order_no_payment_id(
        self, client: AsyncClient, db_session: AsyncSession, test_order: Order
    ):
        """Test cannot refund order without payment ID."""
        test_order.payment_id = None
        await db_session.commit()

        response = await client.post(
            f"/api/v1/orders/{test_order.id}/refund",
            json={},
        )
        assert response.status_code == 400
        assert "payment id" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refund_non_square_payment(
        self, client: AsyncClient, db_session: AsyncSession, test_order: Order
    ):
        """Test refund only works for Square payments."""
        test_order.payment_provider = "stripe"
        await db_session.commit()

        response = await client.post(
            f"/api/v1/orders/{test_order.id}/refund",
            json={},
        )
        assert response.status_code == 400
        assert "square" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refund_order_not_found(self, client: AsyncClient):
        """Test refunding non-existent order returns 404."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/orders/{fake_id}/refund",
            json={},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_refund_restores_inventory(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_order: Order,
        test_product_for_orders: Product,
    ):
        """Test refund restores inventory if order was fulfilled."""
        # Mark order as fulfilled
        test_order.fulfilled_at = datetime.now(timezone.utc)
        await db_session.commit()

        with (
            patch("app.services.square_payment.get_payment_service") as mock_payment,
            patch("app.services.order_fulfillment.OrderFulfillmentService") as mock_fulfillment,
        ):
            mock_service = MagicMock()
            mock_service.refund_payment.return_value = {
                "success": True,
                "refund_id": "refund_789",
                "status": "COMPLETED",
            }
            mock_payment.return_value = mock_service

            mock_fulfillment_instance = MagicMock()
            # Use AsyncMock for the async revert_inventory method
            mock_fulfillment_instance.revert_inventory = AsyncMock(
                return_value=MagicMock(success=True)
            )
            mock_fulfillment.return_value = mock_fulfillment_instance

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/refund",
                json={},
            )

            assert response.status_code == 200
            assert "inventory restored" in response.json()["message"].lower()
            mock_fulfillment_instance.revert_inventory.assert_called_once()


# ============================================
# POST /orders/{id}/resend-email Tests
# ============================================


class TestResendOrderEmail:
    """Tests for POST /orders/{id}/resend-email endpoint."""

    @pytest.mark.asyncio
    async def test_resend_confirmation_email(self, client: AsyncClient, test_order: Order):
        """Test resending order confirmation email."""
        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_service = MagicMock()
            mock_service.send_order_confirmation.return_value = True
            mock_get_email.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/resend-email",
                json={"email_type": "confirmation"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_sent"] is True
            assert "confirmation" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_shipped_email(
        self, client: AsyncClient, db_session: AsyncSession, test_order: Order
    ):
        """Test resending shipped notification email."""
        test_order.status = OrderStatus.SHIPPED
        test_order.shipped_at = datetime.now(timezone.utc)
        await db_session.commit()

        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_service = MagicMock()
            mock_service.send_order_shipped.return_value = True
            mock_get_email.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/resend-email",
                json={"email_type": "shipped"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_sent"] is True
            assert "shipped" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_shipped_email_not_shipped_yet(
        self, client: AsyncClient, test_order: Order
    ):
        """Test cannot resend shipped email if order not shipped."""
        response = await client.post(
            f"/api/v1/orders/{test_order.id}/resend-email",
            json={"email_type": "shipped"},
        )
        assert response.status_code == 400
        assert "not been shipped" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resend_delivered_email(
        self, client: AsyncClient, db_session: AsyncSession, test_order: Order
    ):
        """Test resending delivered notification email."""
        test_order.status = OrderStatus.DELIVERED
        test_order.delivered_at = datetime.now(timezone.utc)
        await db_session.commit()

        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_service = MagicMock()
            mock_service.send_order_delivered.return_value = True
            mock_get_email.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/resend-email",
                json={"email_type": "delivered"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_sent"] is True

    @pytest.mark.asyncio
    async def test_resend_delivered_email_not_delivered_yet(
        self, client: AsyncClient, db_session: AsyncSession, test_order: Order
    ):
        """Test cannot resend delivered email if order not delivered."""
        test_order.status = OrderStatus.SHIPPED
        await db_session.commit()

        response = await client.post(
            f"/api/v1/orders/{test_order.id}/resend-email",
            json={"email_type": "delivered"},
        )
        assert response.status_code == 400
        assert "not been delivered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resend_email_invalid_type(self, client: AsyncClient, test_order: Order):
        """Test invalid email type returns 400."""
        response = await client.post(
            f"/api/v1/orders/{test_order.id}/resend-email",
            json={"email_type": "invalid_type"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resend_email_order_not_found(self, client: AsyncClient):
        """Test resending email for non-existent order returns 404."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/orders/{fake_id}/resend-email",
            json={"email_type": "confirmation"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resend_email_service_failure(self, client: AsyncClient, test_order: Order):
        """Test email service failure returns appropriate response."""
        with patch("app.services.email_service.get_email_service") as mock_get_email:
            mock_service = MagicMock()
            mock_service.send_order_confirmation.return_value = False
            mock_get_email.return_value = mock_service

            response = await client.post(
                f"/api/v1/orders/{test_order.id}/resend-email",
                json={"email_type": "confirmation"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_sent"] is False
            assert "failed" in data["message"].lower()
