"""
Tests for order fulfillment service.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.tenant import Tenant
from app.services.order_fulfillment import OrderFulfillmentService


@pytest.fixture
async def test_product_with_stock(db_session: AsyncSession, test_tenant: Tenant) -> Product:
    """Create a test product with stock."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="FULFILL-001",
        name="Test Product For Fulfillment",
        description="Test product for fulfillment tests",
        units_in_stock=10,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_product_low_stock(db_session: AsyncSession, test_tenant: Tenant) -> Product:
    """Create a test product with low stock."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="FULFILL-002",
        name="Low Stock Product",
        description="Product with low stock",
        units_in_stock=2,
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
    test_product_with_stock: Product,
) -> Order:
    """Create a test order with items."""
    order = Order(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="TEST-ORDER-001",
        status=OrderStatus.PENDING,
        customer_email="test@example.com",
        customer_name="Test Customer",
        shipping_address_line1="123 Test St",
        shipping_city="Test City",
        shipping_postcode="TE1 1ST",
        shipping_country="United Kingdom",
        shipping_method="Test Shipping",
        shipping_cost=Decimal("5.00"),
        subtotal=Decimal("20.00"),
        total=Decimal("25.00"),
        currency="GBP",
        payment_provider="test",
        payment_status="completed",
    )
    db_session.add(order)
    await db_session.flush()

    # Add order item
    item = OrderItem(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_id=order.id,
        product_id=test_product_with_stock.id,
        product_sku=test_product_with_stock.sku,
        product_name=test_product_with_stock.name,
        quantity=3,
        unit_price=Decimal("6.67"),
        total_price=Decimal("20.00"),
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(order)
    return order


class TestOrderFulfillmentService:
    """Tests for OrderFulfillmentService."""

    @pytest.mark.asyncio
    async def test_validate_inventory_success(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_order: Order,
    ):
        """Test validating inventory when sufficient stock exists."""
        service = OrderFulfillmentService(db_session, test_tenant)
        result = await service.validate_inventory(test_order)

        assert result.success is True
        assert len(result.insufficient_items) == 0
        assert "sufficient inventory" in result.message.lower()

    @pytest.mark.asyncio
    async def test_validate_inventory_insufficient(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_product_low_stock: Product,
    ):
        """Test validating inventory when insufficient stock exists."""
        # Create order needing more than available
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="TEST-ORDER-002",
            status=OrderStatus.PENDING,
            customer_email="test@example.com",
            customer_name="Test Customer",
            shipping_address_line1="123 Test St",
            shipping_city="Test City",
            shipping_postcode="TE1 1ST",
            shipping_country="United Kingdom",
            shipping_method="Test Shipping",
            shipping_cost=Decimal("5.00"),
            subtotal=Decimal("50.00"),
            total=Decimal("55.00"),
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
            product_id=test_product_low_stock.id,
            product_sku=test_product_low_stock.sku,
            product_name=test_product_low_stock.name,
            quantity=5,  # Need 5 but only 2 in stock
            unit_price=Decimal("10.00"),
            total_price=Decimal("50.00"),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(order)

        service = OrderFulfillmentService(db_session, test_tenant)
        result = await service.validate_inventory(order)

        assert result.success is False
        assert len(result.insufficient_items) == 1
        assert result.insufficient_items[0].required == 5
        assert result.insufficient_items[0].available == 2

    @pytest.mark.asyncio
    async def test_deduct_inventory_success(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_order: Order,
        test_product_with_stock: Product,
    ):
        """Test deducting inventory successfully."""
        initial_stock = test_product_with_stock.units_in_stock  # 10

        service = OrderFulfillmentService(db_session, test_tenant)
        result = await service.deduct_inventory(test_order)

        assert result.success is True

        # Refresh product to get updated stock
        await db_session.refresh(test_product_with_stock)
        assert test_product_with_stock.units_in_stock == initial_stock - 3  # Ordered 3

        # Check order is marked as fulfilled
        assert test_order.fulfilled_at is not None

    @pytest.mark.asyncio
    async def test_deduct_inventory_insufficient(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_product_low_stock: Product,
    ):
        """Test deducting inventory fails with insufficient stock."""
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="TEST-ORDER-003",
            status=OrderStatus.PENDING,
            customer_email="test@example.com",
            customer_name="Test Customer",
            shipping_address_line1="123 Test St",
            shipping_city="Test City",
            shipping_postcode="TE1 1ST",
            shipping_country="United Kingdom",
            shipping_method="Test Shipping",
            shipping_cost=Decimal("5.00"),
            subtotal=Decimal("50.00"),
            total=Decimal("55.00"),
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
            product_id=test_product_low_stock.id,
            product_sku=test_product_low_stock.sku,
            product_name=test_product_low_stock.name,
            quantity=5,  # Need 5 but only 2 in stock
            unit_price=Decimal("10.00"),
            total_price=Decimal("50.00"),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(order)

        service = OrderFulfillmentService(db_session, test_tenant)
        result = await service.deduct_inventory(order)

        assert result.success is False
        assert len(result.insufficient_items) == 1

        # Stock should not be changed
        await db_session.refresh(test_product_low_stock)
        assert test_product_low_stock.units_in_stock == 2

    @pytest.mark.asyncio
    async def test_revert_inventory_success(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_order: Order,
        test_product_with_stock: Product,
    ):
        """Test reverting inventory after cancellation."""
        initial_stock = test_product_with_stock.units_in_stock

        service = OrderFulfillmentService(db_session, test_tenant)

        # First fulfill the order
        await service.deduct_inventory(test_order)
        await db_session.refresh(test_product_with_stock)
        assert test_product_with_stock.units_in_stock == initial_stock - 3

        # Now revert
        result = await service.revert_inventory(test_order)

        assert result.success is True

        # Stock should be restored
        await db_session.refresh(test_product_with_stock)
        assert test_product_with_stock.units_in_stock == initial_stock

        # Order should no longer be marked fulfilled
        assert test_order.fulfilled_at is None

    @pytest.mark.asyncio
    async def test_revert_inventory_not_fulfilled(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_order: Order,
    ):
        """Test reverting inventory on unfulfilled order does nothing."""
        service = OrderFulfillmentService(db_session, test_tenant)

        # Order not fulfilled, revert should succeed but do nothing
        result = await service.revert_inventory(test_order)

        assert result.success is True
        assert "not fulfilled" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_low_stock_alerts(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_product_low_stock: Product,
    ):
        """Test low stock alerts are triggered."""
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="TEST-ORDER-004",
            status=OrderStatus.PENDING,
            customer_email="test@example.com",
            customer_name="Test Customer",
            shipping_address_line1="123 Test St",
            shipping_city="Test City",
            shipping_postcode="TE1 1ST",
            shipping_country="United Kingdom",
            shipping_method="Test Shipping",
            shipping_cost=Decimal("5.00"),
            subtotal=Decimal("10.00"),
            total=Decimal("15.00"),
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
            product_id=test_product_low_stock.id,
            product_sku=test_product_low_stock.sku,
            product_name=test_product_low_stock.name,
            quantity=1,  # Take 1, leaving 1 in stock
            unit_price=Decimal("10.00"),
            total_price=Decimal("10.00"),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(order)

        service = OrderFulfillmentService(db_session, test_tenant)

        # Fulfill and then check for alerts
        await service.deduct_inventory(order)
        alerts = await service.check_low_stock_alerts(order)

        # Should have an alert since stock is now 1 (below threshold of 5)
        assert len(alerts) == 1
        assert alerts[0]["product_sku"] == test_product_low_stock.sku
        assert alerts[0]["current_stock"] == 1

    @pytest.mark.asyncio
    async def test_deduct_inventory_deleted_product(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ):
        """Test deducting inventory handles deleted products gracefully."""
        # Create order with NULL product_id (simulating deleted product)
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="TEST-ORDER-005",
            status=OrderStatus.PENDING,
            customer_email="test@example.com",
            customer_name="Test Customer",
            shipping_address_line1="123 Test St",
            shipping_city="Test City",
            shipping_postcode="TE1 1ST",
            shipping_country="United Kingdom",
            shipping_method="Test Shipping",
            shipping_cost=Decimal("5.00"),
            subtotal=Decimal("10.00"),
            total=Decimal("15.00"),
            currency="GBP",
            payment_provider="test",
            payment_status="completed",
        )
        db_session.add(order)
        await db_session.flush()

        # Item with no product_id (product was deleted)
        item = OrderItem(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_id=order.id,
            product_id=None,  # Deleted product
            product_sku="DELETED-001",
            product_name="Deleted Product",
            quantity=1,
            unit_price=Decimal("10.00"),
            total_price=Decimal("10.00"),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(order)

        service = OrderFulfillmentService(db_session, test_tenant)
        result = await service.deduct_inventory(order)

        # Should succeed but skip the deleted product
        assert result.success is True
        assert order.fulfilled_at is not None
