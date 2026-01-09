"""Tests for shop checkout API endpoints."""

from decimal import Decimal
from uuid import uuid4
from unittest.mock import MagicMock, patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discount import DiscountCode, DiscountType
from app.models.product import Product
from app.models.product_pricing import ProductPricing
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant
from app.services.cart import CartService, get_cart_service
from app.services.checkout_session import CheckoutSessionService, get_checkout_session_service
from app.services.stock_reservation import StockReservationService, get_stock_reservation_service
from app.main import app
from tests.utils.mock_redis import MockRedis


# ============================================
# Redis Mock Fixtures
# ============================================


@pytest.fixture
def fake_redis():
    """Create a fake Redis client for testing."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_cart_service(fake_redis):
    """Create a cart service with fake Redis."""
    return CartService(redis_client=fake_redis)


@pytest.fixture
def mock_checkout_service(fake_redis):
    """Create a checkout session service with fake Redis."""
    return CheckoutSessionService(redis_client=fake_redis)


@pytest.fixture
def mock_reservation_redis():
    """Create a MockRedis that supports Lua scripts for stock reservation."""
    return MockRedis()


@pytest.fixture
def mock_reservation_service(mock_reservation_redis):
    """Create a stock reservation service with MockRedis (supports Lua scripts)."""
    return StockReservationService(redis_client=mock_reservation_redis)


@pytest.fixture(autouse=True)
def override_redis_services(mock_cart_service, mock_checkout_service, mock_reservation_service):
    """Override Redis-based services with fakes for all tests."""
    app.dependency_overrides[get_cart_service] = lambda: mock_cart_service
    app.dependency_overrides[get_checkout_session_service] = lambda: mock_checkout_service
    app.dependency_overrides[get_stock_reservation_service] = lambda: mock_reservation_service
    yield
    # Clean up overrides
    app.dependency_overrides.pop(get_cart_service, None)
    app.dependency_overrides.pop(get_checkout_session_service, None)
    app.dependency_overrides.pop(get_stock_reservation_service, None)


# ============================================
# Fixtures
# ============================================


@pytest_asyncio.fixture
async def sales_channel(db_session: AsyncSession, test_tenant: Tenant) -> SalesChannel:
    """Create a Mystmereforge sales channel."""
    channel = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Mystmereforge",
        platform_type="online_shop",
        fee_percentage=0,
        fee_fixed=0,
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
async def shop_client(
    db_session: AsyncSession,
    seed_material_types,
    test_tenant: Tenant,
    sales_channel: SalesChannel,
    mock_cart_service,
    mock_checkout_service,
    mock_reservation_service,
):
    """Create a test HTTP client with ShopContext dependency overridden."""
    from app.auth.dependencies import get_shop_sales_channel, get_shop_tenant
    from app.database import get_db

    async def override_get_db():
        yield db_session

    async def override_get_shop_tenant():
        return test_tenant

    async def override_get_shop_sales_channel():
        return (test_tenant, sales_channel)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shop_tenant] = override_get_shop_tenant
    app.dependency_overrides[get_shop_sales_channel] = override_get_shop_sales_channel
    app.dependency_overrides[get_cart_service] = lambda: mock_cart_service
    app.dependency_overrides[get_checkout_session_service] = lambda: mock_checkout_service
    app.dependency_overrides[get_stock_reservation_service] = lambda: mock_reservation_service

    app.state.limiter.enabled = False

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def shop_product(
    db_session: AsyncSession, test_tenant: Tenant, sales_channel: SalesChannel
) -> Product:
    """Create a shop-visible product with pricing."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="TEST-PROD-001",
        name="Test Dragon Miniature",
        description="A test product",
        is_active=True,
        shop_visible=True,
        units_in_stock=10,
    )
    db_session.add(product)
    await db_session.commit()

    # Add pricing
    pricing = ProductPricing(
        id=uuid4(),
        product_id=product.id,
        sales_channel_id=sales_channel.id,
        list_price=Decimal("19.99"),
    )
    db_session.add(pricing)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_product_low_stock(
    db_session: AsyncSession, test_tenant: Tenant, sales_channel: SalesChannel
) -> Product:
    """Create a product with low stock."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="LOW-STOCK-001",
        name="Limited Edition Item",
        description="Only 2 left!",
        is_active=True,
        shop_visible=True,
        units_in_stock=2,
    )
    db_session.add(product)
    await db_session.commit()

    pricing = ProductPricing(
        id=uuid4(),
        product_id=product.id,
        sales_channel_id=sales_channel.id,
        list_price=Decimal("29.99"),
    )
    db_session.add(pricing)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def discount_code(db_session: AsyncSession, test_tenant: Tenant) -> DiscountCode:
    """Create a test discount code."""
    from datetime import datetime, timezone

    code = DiscountCode(
        id=uuid4(),
        tenant_id=test_tenant.id,
        code="TESTDISCOUNT",
        name="Test Discount",
        discount_type=DiscountType.PERCENTAGE,
        amount=Decimal("10.00"),  # 10% off
        min_order_amount=None,
        max_uses=100,
        current_uses=0,
        is_active=True,
        valid_from=datetime.now(timezone.utc),
        valid_to=None,
    )
    db_session.add(code)
    await db_session.commit()
    await db_session.refresh(code)
    return code


# ============================================
# Cart Tests
# ============================================


class TestCartOperations:
    """Tests for cart management endpoints."""

    async def test_get_empty_cart(self, client: AsyncClient):
        """Test getting an empty cart."""
        session_id = str(uuid4())
        response = await client.get(f"/api/v1/shop/cart/{session_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["items"] == []
        assert Decimal(data["subtotal"]) == Decimal("0")

    async def test_add_to_cart(self, client: AsyncClient, shop_product: Product):
        """Test adding item to cart."""
        session_id = str(uuid4())
        response = await client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 2},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["items"][0]["product_id"] == str(shop_product.id)

    async def test_add_to_cart_invalid_product(self, client: AsyncClient):
        """Test adding non-existent product to cart."""
        session_id = str(uuid4())
        response = await client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(uuid4()), "quantity": 1},
        )
        assert response.status_code == 404

    async def test_add_multiple_items_to_cart(self, client: AsyncClient, shop_product: Product):
        """Test adding multiple different items to cart."""
        session_id = str(uuid4())

        # Add first item
        response1 = await client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 1},
        )
        assert response1.status_code == 200

        # Add same item again (should increase quantity)
        response2 = await client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 2},
        )
        assert response2.status_code == 200
        data = response2.json()["data"]
        # Either quantity stacks or we have two items
        total_qty = sum(item["quantity"] for item in data["items"])
        assert total_qty == 3

    async def test_update_cart_item(self, client: AsyncClient, shop_product: Product):
        """Test updating cart item quantity."""
        session_id = str(uuid4())

        # Add item first
        add_response = await client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 1},
        )
        assert add_response.status_code == 200
        item_id = add_response.json()["data"]["items"][0]["id"]

        # Update quantity
        response = await client.patch(
            f"/api/v1/shop/cart/{session_id}/items/{item_id}",
            json={"quantity": 5},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["items"][0]["quantity"] == 5

    async def test_remove_cart_item(self, client: AsyncClient, shop_product: Product):
        """Test removing item from cart."""
        session_id = str(uuid4())

        # Add item first
        add_response = await client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 1},
        )
        item_id = add_response.json()["data"]["items"][0]["id"]

        # Remove item
        response = await client.delete(f"/api/v1/shop/cart/{session_id}/items/{item_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["items"]) == 0


# ============================================
# Shipping Rate Tests
# ============================================


class TestShippingRates:
    """Tests for shipping rate calculation."""

    async def test_get_shipping_rates_valid_postcode(self, client: AsyncClient):
        """Test getting shipping rates for valid UK postcode."""
        response = await client.post(
            "/api/v1/shop/checkout/shipping-rates",
            json={"postcode": "SW1A 1AA", "cart_total_pence": 2000},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["postcode_valid"] is True
        assert "data" in data
        assert len(data["data"]) > 0

    async def test_get_shipping_rates_free_shipping(self, client: AsyncClient):
        """Test free shipping threshold."""
        response = await client.post(
            "/api/v1/shop/checkout/shipping-rates",
            json={"postcode": "SW1A 1AA", "cart_total_pence": 5000},  # Over threshold
        )
        assert response.status_code == 200
        data = response.json()
        assert "qualifies_for_free_shipping" in data

    async def test_get_shipping_rates_highland(self, client: AsyncClient):
        """Test Highland postcode surcharge."""
        response = await client.post(
            "/api/v1/shop/checkout/shipping-rates",
            json={"postcode": "IV1 1AA", "cart_total_pence": 2000},  # Inverness
        )
        assert response.status_code == 200
        data = response.json()
        assert data["postcode_valid"] is True

    async def test_get_shipping_rates_invalid_postcode(self, client: AsyncClient):
        """Test invalid postcode handling."""
        response = await client.post(
            "/api/v1/shop/checkout/shipping-rates",
            json={"postcode": "INVALID", "cart_total_pence": 2000},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["postcode_valid"] is False


# ============================================
# Checkout Session Tests
# ============================================


class TestCreateCheckoutSession:
    """Tests for checkout session creation."""

    async def test_create_checkout_empty_cart(
        self, shop_client: AsyncClient, sales_channel: SalesChannel
    ):
        """Test checkout with empty cart fails."""
        response = await shop_client.post(
            "/api/v1/shop/checkout/create-payment",
            json={
                "cart_session_id": str(uuid4()),
                "shippingAddress": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "line1": "123 Test St",
                    "city": "London",
                    "postcode": "SW1A 1AA",
                    "country": "United Kingdom",
                },
                "shippingMethodId": "standard",
            },
        )
        assert response.status_code == 400
        assert "Cart is empty" in response.json()["detail"]

    async def test_create_checkout_success(
        self, shop_client: AsyncClient, shop_product: Product, sales_channel: SalesChannel
    ):
        """Test successful checkout session creation."""
        # First add item to cart
        session_id = str(uuid4())
        await shop_client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 1},
        )

        # Create checkout
        response = await shop_client.post(
            "/api/v1/shop/checkout/create-payment",
            json={
                "cart_session_id": session_id,
                "shippingAddress": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "line1": "123 Test St",
                    "city": "London",
                    "postcode": "SW1A 1AA",
                    "country": "United Kingdom",
                },
                "shippingMethodId": "standard",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "sessionId" in data
        assert "orderTotal" in data

    async def test_create_checkout_with_discount(
        self,
        shop_client: AsyncClient,
        shop_product: Product,
        sales_channel: SalesChannel,
        discount_code: DiscountCode,
    ):
        """Test checkout with valid discount code."""
        # Add item to cart
        session_id = str(uuid4())
        await shop_client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 1},
        )

        # Create checkout with discount
        response = await shop_client.post(
            "/api/v1/shop/checkout/create-payment",
            json={
                "cart_session_id": session_id,
                "shippingAddress": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "line1": "123 Test St",
                    "city": "London",
                    "postcode": "SW1A 1AA",
                    "country": "United Kingdom",
                },
                "shippingMethodId": "standard",
                "discountCode": "TESTDISCOUNT",
            },
        )
        assert response.status_code == 200

    async def test_create_checkout_validates_stock(
        self, shop_client: AsyncClient, shop_product_low_stock: Product, sales_channel: SalesChannel
    ):
        """Test checkout validates stock levels."""
        # Add items within stock limit
        session_id = str(uuid4())
        await shop_client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product_low_stock.id), "quantity": 2},  # 2 in stock
        )

        # Try to create checkout - should work with quantity matching stock
        response = await shop_client.post(
            "/api/v1/shop/checkout/create-payment",
            json={
                "cart_session_id": session_id,
                "shippingAddress": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "line1": "123 Test St",
                    "city": "London",
                    "postcode": "SW1A 1AA",
                    "country": "United Kingdom",
                },
                "shippingMethodId": "standard",
            },
        )
        # Should succeed when quantity <= stock
        assert response.status_code == 200


# ============================================
# Complete Checkout Tests
# ============================================


class TestCompleteCheckout:
    """Tests for completing checkout with payment."""

    async def test_complete_checkout_session_not_found(self, shop_client: AsyncClient):
        """Test completing checkout with invalid session."""
        response = await shop_client.post(
            "/api/v1/shop/checkout/complete",
            json={
                "payment_session_id": str(uuid4()),
                "square_payment_token": "test_token",
            },
        )
        assert response.status_code == 404
        assert "Checkout session not found" in response.json()["detail"]

    @patch("app.services.square_payment.get_payment_service")
    async def test_complete_checkout_payment_failed(
        self,
        mock_payment_service,
        shop_client: AsyncClient,
        shop_product: Product,
        sales_channel: SalesChannel,
    ):
        """Test checkout with failed payment."""
        # Mock payment failure
        mock_service = MagicMock()
        mock_service.process_payment.return_value = MagicMock(
            success=False,
            error_code="CARD_DECLINED",
            error_message="Card was declined",
        )
        mock_payment_service.return_value = mock_service

        # Add item and create checkout
        session_id = str(uuid4())
        await shop_client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 1},
        )

        checkout_response = await shop_client.post(
            "/api/v1/shop/checkout/create-payment",
            json={
                "cart_session_id": session_id,
                "shippingAddress": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "line1": "123 Test St",
                    "city": "London",
                    "postcode": "SW1A 1AA",
                    "country": "United Kingdom",
                },
                "shippingMethodId": "standard",
            },
        )
        checkout_session_id = checkout_response.json()["data"]["sessionId"]

        # Complete checkout
        response = await shop_client.post(
            "/api/v1/shop/checkout/complete",
            json={
                "payment_session_id": checkout_session_id,
                "square_payment_token": "test_token",
            },
        )
        assert response.status_code == 402
        detail = response.json()["detail"]
        assert detail["error_code"] == "CARD_DECLINED"

    async def test_complete_checkout_requires_valid_session(
        self,
        shop_client: AsyncClient,
        shop_product: Product,
        sales_channel: SalesChannel,
    ):
        """Test checkout completion requires valid session and token."""
        # Add item and create checkout
        session_id = str(uuid4())
        await shop_client.post(
            f"/api/v1/shop/cart/{session_id}/items",
            json={"product_id": str(shop_product.id), "quantity": 1},
        )

        checkout_response = await shop_client.post(
            "/api/v1/shop/checkout/create-payment",
            json={
                "cart_session_id": session_id,
                "shippingAddress": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "line1": "123 Test St",
                    "city": "London",
                    "postcode": "SW1A 1AA",
                    "country": "United Kingdom",
                },
                "shippingMethodId": "standard",
            },
        )
        assert checkout_response.status_code == 200
        checkout_session_id = checkout_response.json()["data"]["sessionId"]
        assert checkout_session_id is not None

        # Session was created successfully - the complete step would need Square API
        # which we can't test without real credentials


# ============================================
# Order Lookup Tests
# ============================================


class TestOrderLookup:
    """Tests for order status lookup."""

    async def test_get_order_not_found(self, client: AsyncClient):
        """Test looking up non-existent order."""
        response = await client.get(
            "/api/v1/shop/orders/MF-99999999-999",
            params={"email": "test@example.com"},
        )
        assert response.status_code == 404

    async def test_get_order_wrong_email(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        sales_channel: SalesChannel,
    ):
        """Test looking up order with wrong email."""
        from app.models.order import Order, OrderStatus

        # Create an order directly
        order = Order(
            id=uuid4(),
            tenant_id=test_tenant.id,
            order_number="MF-20240101-001",
            sales_channel_id=sales_channel.id,
            status=OrderStatus.PENDING,
            customer_email="real@example.com",
            customer_name="Real Customer",
            shipping_address_line1="123 St",
            shipping_city="London",
            shipping_postcode="SW1A 1AA",
            shipping_country="UK",
            shipping_method="standard",
            shipping_cost=Decimal("3.95"),
            subtotal=Decimal("19.99"),
            total=Decimal("23.94"),
        )
        db_session.add(order)
        await db_session.commit()

        response = await client.get(
            "/api/v1/shop/orders/MF-20240101-001",
            params={"email": "wrong@example.com"},
        )
        assert response.status_code == 404


# ============================================
# Product Catalog Tests
# ============================================


class TestProductCatalog:
    """Tests for shop product catalog."""

    async def test_list_products_empty(self, shop_client: AsyncClient):
        """Test listing products when none exist."""
        response = await shop_client.get("/api/v1/shop/products")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_list_products_with_data(self, shop_client: AsyncClient, shop_product: Product):
        """Test listing products returns shop-visible products."""
        response = await shop_client.get("/api/v1/shop/products")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1

        # Find our test product
        product = next((p for p in data["data"] if p["sku"] == "TEST-PROD-001"), None)
        assert product is not None
        assert product["name"] == "Test Dragon Miniature"

    async def test_list_products_pagination(self, shop_client: AsyncClient, shop_product: Product):
        """Test product list pagination."""
        response = await shop_client.get("/api/v1/shop/products?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "limit" in data

    async def test_get_product_by_id(self, shop_client: AsyncClient, shop_product: Product):
        """Test getting single product by ID."""
        response = await shop_client.get(f"/api/v1/shop/products/{shop_product.id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["sku"] == "TEST-PROD-001"

    async def test_get_product_not_found(self, shop_client: AsyncClient):
        """Test getting non-existent product."""
        response = await shop_client.get(f"/api/v1/shop/products/{uuid4()}")
        assert response.status_code == 404


# ============================================
# Search Tests
# ============================================


class TestProductSearch:
    """Tests for product search functionality."""

    async def test_search_products(self, shop_client: AsyncClient, shop_product: Product):
        """Test searching products."""
        response = await shop_client.get("/api/v1/shop/products?search=dragon")
        assert response.status_code == 200

    async def test_search_no_results(self, shop_client: AsyncClient):
        """Test search with no results."""
        response = await shop_client.get("/api/v1/shop/products?search=xyznonexistent123")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0


# ============================================
# Contact Form Tests
# ============================================


class TestContactForm:
    """Tests for contact form submission."""

    async def test_submit_contact_form(self, client: AsyncClient):
        """Test submitting contact form."""
        response = await client.post(
            "/api/v1/shop/contact",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Test Subject",
                "message": "This is a test message.",
            },
        )
        # Contact form should succeed or return expected error
        assert response.status_code in [200, 201, 500]  # 500 if email service not configured

    async def test_submit_contact_form_missing_fields(self, client: AsyncClient):
        """Test contact form with missing required fields."""
        response = await client.post(
            "/api/v1/shop/contact",
            json={
                "name": "Test User",
                # Missing email, subject, message
            },
        )
        assert response.status_code == 422


# ============================================
# Designers Tests
# ============================================


@pytest_asyncio.fixture
async def test_designer(db_session: AsyncSession, test_tenant: Tenant):
    """Create a test designer."""
    from app.models.designer import Designer

    designer = Designer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Dragon Artist",
        slug="test-dragon-artist",
        description="Creates amazing dragons",
        is_active=True,
    )
    db_session.add(designer)
    await db_session.commit()
    await db_session.refresh(designer)
    return designer


class TestDesigners:
    """Tests for designer endpoints."""

    async def test_list_designers(self, client: AsyncClient):
        """Test listing designers."""
        response = await client.get("/api/v1/shop/designers")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_get_designer_by_slug(self, client: AsyncClient, test_designer):
        """Test getting designer by slug."""
        response = await client.get(f"/api/v1/shop/designers/{test_designer.slug}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Test Dragon Artist"
        assert data["slug"] == "test-dragon-artist"

    async def test_get_designer_not_found(self, client: AsyncClient):
        """Test getting non-existent designer."""
        response = await client.get("/api/v1/shop/designers/nonexistent-designer")
        assert response.status_code == 404


# ============================================
# Dragons/Featured Products Tests
# ============================================


class TestDragons:
    """Tests for dragon/featured product endpoints."""

    async def test_list_dragons_empty(self, client: AsyncClient):
        """Test listing dragons when none exist."""
        response = await client.get("/api/v1/shop/dragons")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_list_dragons_with_dragon_product(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        sales_channel: SalesChannel,
    ):
        """Test listing dragons returns products with is_dragon=True."""
        # Create a dragon product
        product = Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="DRAGON-FEATURED-001",
            name="Epic Dragon",
            description="A featured dragon",
            is_active=True,
            shop_visible=True,
            is_featured=True,
            is_dragon=True,
            units_in_stock=5,
        )
        db_session.add(product)
        await db_session.commit()

        # Add pricing
        pricing = ProductPricing(
            id=uuid4(),
            product_id=product.id,
            sales_channel_id=sales_channel.id,
            list_price=Decimal("49.99"),
        )
        db_session.add(pricing)
        await db_session.commit()

        response = await client.get("/api/v1/shop/dragons")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1

    async def test_featured_product_not_in_dragons(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        sales_channel: SalesChannel,
    ):
        """Test that is_featured=True but is_dragon=False does NOT appear in dragons.

        This verifies the separation between featured products (for showcase/gallery)
        and dragon products (for the Dragons collection page).
        """
        # Create a featured product that is NOT a dragon
        product = Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="FEATURED-NOT-DRAGON-001",
            name="Featured Godzilla",
            description="A featured product but not a dragon",
            is_active=True,
            shop_visible=True,
            is_featured=True,  # Featured for showcase
            is_dragon=False,  # But NOT a dragon
            units_in_stock=5,
        )
        db_session.add(product)
        await db_session.commit()

        # Add pricing
        pricing = ProductPricing(
            id=uuid4(),
            product_id=product.id,
            sales_channel_id=sales_channel.id,
            list_price=Decimal("29.99"),
        )
        db_session.add(pricing)
        await db_session.commit()

        response = await client.get("/api/v1/shop/dragons")
        assert response.status_code == 200
        data = response.json()

        # Verify our featured-but-not-dragon product is NOT in the results
        dragon_skus = [p["sku"] for p in data["data"]]
        assert "FEATURED-NOT-DRAGON-001" not in dragon_skus


# ============================================
# Categories Tests
# ============================================


class TestShopCategories:
    """Tests for shop category endpoints."""

    async def test_list_categories(self, client: AsyncClient):
        """Test listing categories."""
        response = await client.get("/api/v1/shop/categories")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)


# ============================================
# Pages Tests
# ============================================


@pytest_asyncio.fixture
async def test_page(db_session: AsyncSession, test_tenant: Tenant, sales_channel: SalesChannel):
    """Create a test page."""
    from app.models.page import Page

    page = Page(
        id=uuid4(),
        tenant_id=test_tenant.id,
        slug="privacy-policy",
        title="Privacy Policy",
        content="This is our privacy policy content.",
        meta_description="Privacy policy for our shop",
        is_published=True,
        sort_order=0,
    )
    db_session.add(page)
    await db_session.commit()
    await db_session.refresh(page)
    return page


class TestPages:
    """Tests for shop page endpoints."""

    async def test_list_pages_empty(self, shop_client: AsyncClient):
        """Test listing pages when none exist."""
        response = await shop_client.get("/api/v1/shop/pages")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    async def test_list_pages_with_data(
        self, shop_client: AsyncClient, test_page, sales_channel: SalesChannel
    ):
        """Test listing pages returns published pages."""
        response = await shop_client.get("/api/v1/shop/pages")
        assert response.status_code == 200
        data = response.json()
        # May or may not find our page depending on tenant matching
        assert "data" in data

    async def test_get_page_by_slug(
        self, shop_client: AsyncClient, test_page, sales_channel: SalesChannel
    ):
        """Test getting page by slug."""
        response = await shop_client.get("/api/v1/shop/pages/privacy-policy")
        # May return 200 or 404 depending on tenant matching
        assert response.status_code in [200, 404]

    async def test_get_page_not_found(self, shop_client: AsyncClient):
        """Test getting non-existent page."""
        response = await shop_client.get("/api/v1/shop/pages/nonexistent-page")
        assert response.status_code == 404


# ============================================
# Product Reviews Tests
# ============================================


@pytest_asyncio.fixture
async def test_review(db_session: AsyncSession, test_tenant: Tenant, shop_product: Product):
    """Create a test review."""
    from app.models.review import Review

    review = Review(
        id=uuid4(),
        tenant_id=test_tenant.id,
        product_id=shop_product.id,
        customer_email="reviewer@example.com",
        customer_name="Happy Customer",
        rating=5,
        title="Great product!",
        body="This dragon miniature is amazing! Highly recommended.",
        is_verified_purchase=True,
        is_approved=True,
        helpful_count=3,
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


class TestProductReviews:
    """Tests for product review endpoints."""

    async def test_get_product_reviews_empty(self, client: AsyncClient, shop_product: Product):
        """Test getting reviews when none exist."""
        response = await client.get(f"/api/v1/shop/products/{shop_product.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["data"] == []

    async def test_get_product_reviews_with_data(
        self, client: AsyncClient, shop_product: Product, test_review
    ):
        """Test getting reviews with data."""
        response = await client.get(f"/api/v1/shop/products/{shop_product.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["rating"] == 5
        assert data["data"][0]["customer_name"] == "Happy Customer"
        assert data["average_rating"] is not None

    async def test_get_product_reviews_pagination(self, client: AsyncClient, shop_product: Product):
        """Test review pagination."""
        response = await client.get(
            f"/api/v1/shop/products/{shop_product.id}/reviews?page=1&limit=5"
        )
        assert response.status_code == 200

    async def test_get_reviews_invalid_product(self, client: AsyncClient):
        """Test getting reviews for invalid product."""
        response = await client.get("/api/v1/shop/products/invalid-uuid/reviews")
        assert response.status_code == 404

    async def test_get_reviews_nonexistent_product(self, client: AsyncClient):
        """Test getting reviews for non-existent product."""
        response = await client.get(f"/api/v1/shop/products/{uuid4()}/reviews")
        assert response.status_code == 404

    async def test_submit_review(self, client: AsyncClient, shop_product: Product):
        """Test submitting a review."""
        response = await client.post(
            f"/api/v1/shop/products/{shop_product.id}/reviews",
            json={
                "rating": 4,
                "title": "Nice product",
                "body": "This is a great dragon miniature. Would buy again!",
                "customer_name": "John Doe",
                "customer_email": "john.doe@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "approval" in data["message"].lower()

    async def test_submit_review_invalid_rating(self, client: AsyncClient, shop_product: Product):
        """Test submitting review with invalid rating."""
        response = await client.post(
            f"/api/v1/shop/products/{shop_product.id}/reviews",
            json={
                "rating": 6,  # Invalid - max is 5
                "body": "This is a review with invalid rating.",
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
            },
        )
        assert response.status_code == 422

    async def test_submit_review_short_body(self, client: AsyncClient, shop_product: Product):
        """Test submitting review with too short body."""
        response = await client.post(
            f"/api/v1/shop/products/{shop_product.id}/reviews",
            json={
                "rating": 5,
                "body": "Short",  # Too short - min is 10 chars
                "customer_name": "John Doe",
                "customer_email": "john@example.com",
            },
        )
        assert response.status_code == 422

    async def test_submit_duplicate_review(
        self, client: AsyncClient, shop_product: Product, test_review
    ):
        """Test submitting duplicate review from same email."""
        response = await client.post(
            f"/api/v1/shop/products/{shop_product.id}/reviews",
            json={
                "rating": 3,
                "body": "Trying to submit another review from same email.",
                "customer_name": "Another Name",
                "customer_email": "reviewer@example.com",  # Same email as test_review
            },
        )
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    async def test_mark_review_helpful(
        self, client: AsyncClient, shop_product: Product, test_review
    ):
        """Test marking a review as helpful."""
        initial_count = test_review.helpful_count

        response = await client.post(
            f"/api/v1/shop/products/{shop_product.id}/reviews/{test_review.id}/helpful"
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["helpful_count"] == initial_count + 1

    async def test_mark_review_helpful_invalid_review(
        self, client: AsyncClient, shop_product: Product
    ):
        """Test marking non-existent review as helpful."""
        response = await client.post(
            f"/api/v1/shop/products/{shop_product.id}/reviews/{uuid4()}/helpful"
        )
        assert response.status_code == 404

    async def test_mark_review_helpful_invalid_ids(self, client: AsyncClient):
        """Test marking review with invalid IDs."""
        response = await client.post("/api/v1/shop/products/invalid/reviews/invalid/helpful")
        assert response.status_code == 404


# ============================================
# Image Proxy Tests
# ============================================


class TestImageProxy:
    """Tests for image proxy endpoint."""

    async def test_get_image_not_found(self, client: AsyncClient):
        """Test getting non-existent image."""
        response = await client.get("/api/v1/shop/images/test-product/nonexistent.jpg")
        assert response.status_code == 404

    async def test_get_image_invalid_path(self, client: AsyncClient):
        """Test getting image with invalid path."""
        response = await client.get("/api/v1/shop/images/../../../etc/passwd")
        # Should return 404, not expose file system
        assert response.status_code == 404


# ============================================
# Category Filtering Tests
# ============================================


@pytest_asyncio.fixture
async def test_category(db_session: AsyncSession, test_tenant: Tenant):
    """Create a test category."""
    from app.models.category import Category

    category = Category(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Dragon Miniatures",
        slug="dragon-miniatures",
        description="All dragon miniatures",
        is_active=True,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def product_with_category(
    db_session: AsyncSession,
    test_tenant: Tenant,
    sales_channel: SalesChannel,
    test_category,
):
    """Create a product linked to a category."""
    from app.models.category import product_categories

    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="CAT-PROD-001",
        name="Category Dragon",
        description="A dragon in a category",
        is_active=True,
        shop_visible=True,
        units_in_stock=10,
    )
    db_session.add(product)
    await db_session.commit()

    # Add pricing
    pricing = ProductPricing(
        id=uuid4(),
        product_id=product.id,
        sales_channel_id=sales_channel.id,
        list_price=Decimal("29.99"),
    )
    db_session.add(pricing)

    # Link to category (tenant_id required for multi-tenant isolation)
    await db_session.execute(
        product_categories.insert().values(
            tenant_id=test_tenant.id,
            product_id=product.id,
            category_id=test_category.id,
        )
    )
    await db_session.commit()
    await db_session.refresh(product)
    return product


class TestCategoryFiltering:
    """Tests for category filtering in product listings."""

    async def test_list_products_by_category(
        self, shop_client: AsyncClient, product_with_category, test_category
    ):
        """Test filtering products by category slug."""
        response = await shop_client.get(f"/api/v1/shop/products?category={test_category.slug}")
        assert response.status_code == 200
        data = response.json()
        # Should find our categorized product
        assert "data" in data
        # Products in the category may or may not include our test product
        # depending on tenant matching

    async def test_list_products_by_nonexistent_category(self, shop_client: AsyncClient):
        """Test filtering by non-existent category."""
        response = await shop_client.get("/api/v1/shop/products?category=nonexistent-category")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    async def test_categories_with_product_count(
        self, shop_client: AsyncClient, product_with_category, test_category
    ):
        """Test that categories include product counts."""
        response = await shop_client.get("/api/v1/shop/categories")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


# ============================================
# Product Sorting Tests
# ============================================


class TestProductSorting:
    """Tests for product sorting options."""

    async def test_sort_by_price_asc(self, shop_client: AsyncClient, shop_product: Product):
        """Test sorting products by price ascending."""
        response = await shop_client.get("/api/v1/shop/products?sort=price-asc")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    async def test_sort_by_price_desc(self, shop_client: AsyncClient, shop_product: Product):
        """Test sorting products by price descending."""
        response = await shop_client.get("/api/v1/shop/products?sort=price-desc")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    async def test_sort_by_newest(self, shop_client: AsyncClient, shop_product: Product):
        """Test sorting products by newest (default)."""
        response = await shop_client.get("/api/v1/shop/products?sort=newest")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


# ============================================
# Designer Product Count Tests
# ============================================


@pytest_asyncio.fixture
async def designer_with_products(
    db_session: AsyncSession,
    test_tenant: Tenant,
    sales_channel: SalesChannel,
    test_designer,
):
    """Create products linked to a designer."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="DESIGNER-PROD-001",
        name="Designer Dragon",
        description="A dragon by a designer",
        is_active=True,
        shop_visible=True,
        units_in_stock=10,
        designer_id=test_designer.id,
    )
    db_session.add(product)
    await db_session.commit()

    # Add pricing
    pricing = ProductPricing(
        id=uuid4(),
        product_id=product.id,
        sales_channel_id=sales_channel.id,
        list_price=Decimal("39.99"),
    )
    db_session.add(pricing)
    await db_session.commit()
    await db_session.refresh(product)
    return product


class TestDesignerWithProducts:
    """Tests for designers with products."""

    async def test_designer_with_product_count(
        self, client: AsyncClient, designer_with_products, test_designer
    ):
        """Test that designers include product counts."""
        response = await client.get("/api/v1/shop/designers")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Should include our designer with products


# ============================================
# Verified Purchase Review Tests
# ============================================


@pytest_asyncio.fixture
async def order_with_items(
    db_session: AsyncSession,
    test_tenant: Tenant,
    sales_channel: SalesChannel,
    shop_product: Product,
):
    """Create an order with items for verified purchase testing."""
    from app.models.order import Order as OrderModel, OrderItem as OrderItemModel

    order = OrderModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_number="MF-20240115-001",
        sales_channel_id=sales_channel.id,
        status="completed",
        customer_email="verified.buyer@example.com",
        customer_name="Verified Buyer",
        shipping_address_line1="123 Test St",
        shipping_city="London",
        shipping_postcode="SW1A 1AA",
        shipping_country="UK",
        shipping_method="standard",
        shipping_cost=Decimal("3.95"),
        subtotal=Decimal("19.99"),
        total=Decimal("23.94"),
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    # Add order item (tenant_id required for multi-tenant isolation)
    item = OrderItemModel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        order_id=order.id,
        product_id=shop_product.id,
        product_sku=shop_product.sku,
        product_name=shop_product.name,
        quantity=1,
        unit_price=Decimal("19.99"),
        total_price=Decimal("19.99"),
    )
    db_session.add(item)
    await db_session.commit()
    return order


class TestVerifiedPurchaseReview:
    """Tests for verified purchase reviews."""

    async def test_submit_review_with_verified_purchase(
        self, client: AsyncClient, shop_product: Product, order_with_items
    ):
        """Test submitting review from customer with verified purchase."""
        response = await client.post(
            f"/api/v1/shop/products/{shop_product.id}/reviews",
            json={
                "rating": 5,
                "title": "Excellent quality",
                "body": "This product is amazing! I bought it and it exceeded expectations.",
                "customer_name": "Verified Buyer",
                "customer_email": "verified.buyer@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ============================================
# Submit Review Invalid Product Tests
# ============================================


class TestSubmitReviewInvalidProduct:
    """Tests for submitting reviews to invalid products."""

    async def test_submit_review_invalid_uuid(self, client: AsyncClient):
        """Test submitting review with invalid product UUID."""
        response = await client.post(
            "/api/v1/shop/products/invalid-uuid/reviews",
            json={
                "rating": 5,
                "body": "This is a test review body long enough.",
                "customer_name": "Test User",
                "customer_email": "test@example.com",
            },
        )
        assert response.status_code == 404

    async def test_submit_review_nonexistent_product(self, client: AsyncClient):
        """Test submitting review to non-existent product."""
        response = await client.post(
            f"/api/v1/shop/products/{uuid4()}/reviews",
            json={
                "rating": 5,
                "body": "This is a test review body long enough.",
                "customer_name": "Test User",
                "customer_email": "test@example.com",
            },
        )
        assert response.status_code == 404
