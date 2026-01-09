"""Tests for customer account API endpoints."""

from decimal import Decimal
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerAddress
from app.models.order import Order, OrderItem, OrderStatus
from app.models.tenant import Tenant


# ============================================
# Fixtures
# ============================================


@pytest_asyncio.fixture
async def customer_address(
    db_session: AsyncSession,
    test_customer: Customer,
) -> CustomerAddress:
    """Create a test customer address."""
    address = CustomerAddress(
        id=uuid4(),
        customer_id=test_customer.id,
        tenant_id=test_customer.tenant_id,
        label="Home",
        is_default=True,
        recipient_name="Test Customer",
        phone="07700900000",
        line1="123 Test Street",
        line2="Apt 1",
        city="London",
        county="Greater London",
        postcode="SW1A 1AA",
        country="GB",
    )
    db_session.add(address)
    await db_session.commit()
    await db_session.refresh(address)
    return address


@pytest_asyncio.fixture
async def second_address(
    db_session: AsyncSession,
    test_customer: Customer,
) -> CustomerAddress:
    """Create a second customer address."""
    address = CustomerAddress(
        id=uuid4(),
        customer_id=test_customer.id,
        tenant_id=test_customer.tenant_id,
        label="Work",
        is_default=False,
        recipient_name="Test Customer",
        phone="07700900001",
        line1="456 Office Road",
        city="Manchester",
        postcode="M1 1AA",
        country="GB",
    )
    db_session.add(address)
    await db_session.commit()
    await db_session.refresh(address)
    return address


@pytest_asyncio.fixture
async def customer_order(
    db_session: AsyncSession,
    test_customer: Customer,
    test_tenant: Tenant,
) -> Order:
    """Create a test order for the customer."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="ORD-TEST-001",
        status=OrderStatus.DELIVERED,
        customer_email=test_customer.email,
        customer_name=test_customer.full_name,
        shipping_address_line1="123 Test Street",
        shipping_city="London",
        shipping_postcode="SW1A 1AA",
        shipping_country="United Kingdom",
        shipping_method="Standard",
        shipping_cost=Decimal("4.99"),
        subtotal=Decimal("29.99"),
        total=Decimal("34.98"),
        currency="GBP",
        payment_provider="square",
        payment_status="completed",
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_id=order.id,
        product_name="Test Product",
        product_sku="TEST-001",
        quantity=1,
        unit_price=Decimal("29.99"),
        total_price=Decimal("29.99"),
    )
    db_session.add(item)

    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest_asyncio.fixture
async def shipped_order(
    db_session: AsyncSession,
    test_customer: Customer,
    test_tenant: Tenant,
) -> Order:
    """Create a shipped order (returnable)."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="ORD-TEST-002",
        status=OrderStatus.SHIPPED,
        customer_email=test_customer.email,
        customer_name=test_customer.full_name,
        shipping_address_line1="123 Test Street",
        shipping_city="London",
        shipping_postcode="SW1A 1AA",
        shipping_country="United Kingdom",
        shipping_method="Standard",
        shipping_cost=Decimal("4.99"),
        subtotal=Decimal("49.99"),
        total=Decimal("54.98"),
        currency="GBP",
        payment_provider="square",
        payment_status="completed",
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_id=order.id,
        product_name="Shipped Product",
        product_sku="SHIP-001",
        quantity=2,
        unit_price=Decimal("24.99"),
        total_price=Decimal("49.98"),
    )
    db_session.add(item)

    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest_asyncio.fixture
async def pending_order(
    db_session: AsyncSession,
    test_customer: Customer,
    test_tenant: Tenant,
) -> Order:
    """Create a pending order (not returnable)."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="ORD-TEST-003",
        status=OrderStatus.PENDING,
        customer_email=test_customer.email,
        customer_name=test_customer.full_name,
        shipping_address_line1="123 Test Street",
        shipping_city="London",
        shipping_postcode="SW1A 1AA",
        shipping_country="United Kingdom",
        shipping_method="Standard",
        shipping_cost=Decimal("0.00"),
        subtotal=Decimal("19.99"),
        total=Decimal("19.99"),
        currency="GBP",
        payment_provider="square",
        payment_status="completed",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


# ============================================
# Test Classes
# ============================================


class TestCustomerProfile:
    """Tests for customer profile endpoints."""

    async def test_get_profile(
        self,
        customer_client: AsyncClient,
        test_customer: Customer,
    ):
        """Test getting customer profile."""
        response = await customer_client.get("/api/v1/customer/account/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_customer.email
        assert data["full_name"] == test_customer.full_name
        assert "addresses" in data

    async def test_update_profile(
        self,
        customer_client: AsyncClient,
    ):
        """Test updating customer profile."""
        response = await customer_client.put(
            "/api/v1/customer/account/profile",
            json={
                "full_name": "Updated Name",
                "phone": "07700900123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["phone"] == "07700900123"

    async def test_update_profile_marketing_consent(
        self,
        customer_client: AsyncClient,
    ):
        """Test updating marketing consent."""
        response = await customer_client.put(
            "/api/v1/customer/account/profile",
            json={"marketing_consent": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["marketing_consent"] is True

    async def test_profile_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/customer/account/profile")
        assert response.status_code == 401


class TestCustomerAddresses:
    """Tests for customer address endpoints."""

    async def test_list_addresses_empty(
        self,
        customer_client: AsyncClient,
    ):
        """Test listing addresses when empty."""
        response = await customer_client.get("/api/v1/customer/account/addresses")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_addresses(
        self,
        customer_client: AsyncClient,
        customer_address: CustomerAddress,
    ):
        """Test listing addresses."""
        response = await customer_client.get("/api/v1/customer/account/addresses")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_create_address(
        self,
        customer_client: AsyncClient,
    ):
        """Test creating a new address."""
        response = await customer_client.post(
            "/api/v1/customer/account/addresses",
            json={
                "label": "New Address",
                "is_default": False,
                "recipient_name": "Test User",
                "phone": "07700900000",
                "line1": "789 New Road",
                "city": "Birmingham",
                "postcode": "B1 1AA",
                "country": "GB",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "New Address"
        assert data["line1"] == "789 New Road"

    async def test_create_default_address(
        self,
        customer_client: AsyncClient,
        customer_address: CustomerAddress,
    ):
        """Test creating a default address unsets other defaults."""
        response = await customer_client.post(
            "/api/v1/customer/account/addresses",
            json={
                "label": "New Default",
                "is_default": True,
                "recipient_name": "Test User",
                "line1": "New Default St",
                "city": "London",
                "postcode": "E1 1AA",
                "country": "GB",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["is_default"] is True

    async def test_get_address(
        self,
        customer_client: AsyncClient,
        customer_address: CustomerAddress,
    ):
        """Test getting a specific address."""
        response = await customer_client.get(
            f"/api/v1/customer/account/addresses/{customer_address.id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(customer_address.id)
        assert data["label"] == customer_address.label

    async def test_get_address_not_found(
        self,
        customer_client: AsyncClient,
    ):
        """Test getting non-existent address."""
        fake_id = uuid4()
        response = await customer_client.get(f"/api/v1/customer/account/addresses/{fake_id}")
        assert response.status_code == 404

    async def test_update_address(
        self,
        customer_client: AsyncClient,
        customer_address: CustomerAddress,
    ):
        """Test updating an address."""
        response = await customer_client.put(
            f"/api/v1/customer/account/addresses/{customer_address.id}",
            json={"label": "Updated Home", "city": "Manchester"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Updated Home"
        assert data["city"] == "Manchester"

    async def test_update_address_set_default(
        self,
        customer_client: AsyncClient,
        second_address: CustomerAddress,
    ):
        """Test setting an address as default via update."""
        response = await customer_client.put(
            f"/api/v1/customer/account/addresses/{second_address.id}",
            json={"is_default": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True

    async def test_delete_address(
        self,
        customer_client: AsyncClient,
        customer_address: CustomerAddress,
    ):
        """Test deleting an address."""
        response = await customer_client.delete(
            f"/api/v1/customer/account/addresses/{customer_address.id}"
        )
        assert response.status_code == 204

    async def test_delete_address_not_found(
        self,
        customer_client: AsyncClient,
    ):
        """Test deleting non-existent address."""
        fake_id = uuid4()
        response = await customer_client.delete(f"/api/v1/customer/account/addresses/{fake_id}")
        assert response.status_code == 404

    async def test_set_default_address(
        self,
        customer_client: AsyncClient,
        second_address: CustomerAddress,
    ):
        """Test setting an address as default."""
        response = await customer_client.post(
            f"/api/v1/customer/account/addresses/{second_address.id}/set-default"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True

    async def test_set_default_address_not_found(
        self,
        customer_client: AsyncClient,
    ):
        """Test setting non-existent address as default."""
        fake_id = uuid4()
        response = await customer_client.post(
            f"/api/v1/customer/account/addresses/{fake_id}/set-default"
        )
        assert response.status_code == 404


class TestCustomerOrders:
    """Tests for customer order history endpoints."""

    async def test_list_orders_empty(
        self,
        customer_client: AsyncClient,
    ):
        """Test listing orders when empty."""
        response = await customer_client.get("/api/v1/customer/account/orders")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data

    async def test_list_orders(
        self,
        customer_client: AsyncClient,
        customer_order: Order,
    ):
        """Test listing orders."""
        response = await customer_client.get("/api/v1/customer/account/orders")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_list_orders_pagination(
        self,
        customer_client: AsyncClient,
    ):
        """Test order list pagination."""
        response = await customer_client.get("/api/v1/customer/account/orders?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 10

    async def test_get_order(
        self,
        customer_client: AsyncClient,
        customer_order: Order,
    ):
        """Test getting a specific order."""
        response = await customer_client.get(f"/api/v1/customer/account/orders/{customer_order.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(customer_order.id)
        assert data["order_number"] == customer_order.order_number

    async def test_get_order_not_found(
        self,
        customer_client: AsyncClient,
    ):
        """Test getting non-existent order."""
        fake_id = uuid4()
        response = await customer_client.get(f"/api/v1/customer/account/orders/{fake_id}")
        assert response.status_code == 404


class TestCustomerReturns:
    """Tests for customer return request endpoints."""

    async def test_list_returns_empty(
        self,
        customer_client: AsyncClient,
    ):
        """Test listing returns when empty."""
        response = await customer_client.get("/api/v1/customer/account/returns")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_return_not_found(
        self,
        customer_client: AsyncClient,
    ):
        """Test getting non-existent return."""
        fake_id = uuid4()
        response = await customer_client.get(f"/api/v1/customer/account/returns/{fake_id}")
        assert response.status_code == 404

    async def test_create_return_order_not_found(
        self,
        customer_client: AsyncClient,
    ):
        """Test creating return for non-existent order."""
        fake_id = uuid4()
        fake_item_id = uuid4()
        response = await customer_client.post(
            f"/api/v1/customer/account/orders/{fake_id}/return",
            json={
                "reason": "defective",
                "reason_details": "Item is broken",
                "requested_action": "refund",
                "items": [{"order_item_id": str(fake_item_id), "quantity": 1}],
            },
        )
        assert response.status_code == 404

    async def test_create_return_not_shipped(
        self,
        customer_client: AsyncClient,
        pending_order: Order,
    ):
        """Test creating return for non-shipped order fails."""
        fake_item_id = uuid4()
        response = await customer_client.post(
            f"/api/v1/customer/account/orders/{pending_order.id}/return",
            json={
                "reason": "defective",
                "reason_details": "Item is broken",
                "requested_action": "refund",
                "items": [{"order_item_id": str(fake_item_id), "quantity": 1}],
            },
        )
        assert response.status_code == 400
        assert "shipped or delivered" in response.json()["detail"]

    async def test_cancel_return_not_found(
        self,
        customer_client: AsyncClient,
    ):
        """Test cancelling non-existent return."""
        fake_id = uuid4()
        response = await customer_client.post(f"/api/v1/customer/account/returns/{fake_id}/cancel")
        assert response.status_code == 404
