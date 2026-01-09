"""
Tests for Redis-backed cart service.
"""

import pytest
from decimal import Decimal
from uuid import uuid4

import fakeredis.aioredis
from app.services.cart import CartService, Cart, CartItem


@pytest.fixture
def fake_redis():
    """Create a fake Redis client for testing."""
    return fakeredis.aioredis.FakeRedis(encoding="utf-8", decode_responses=True)


@pytest.fixture
def cart_service(fake_redis):
    """Create a cart service with fake Redis."""
    return CartService(redis_client=fake_redis, ttl=3600)


class TestCartService:
    """Tests for CartService."""

    @pytest.mark.asyncio
    async def test_get_cart_empty(self, cart_service):
        """Test getting a cart that doesn't exist returns empty cart."""
        session_id = str(uuid4())
        cart = await cart_service.get_cart(session_id)

        assert cart.session_id == session_id
        assert cart.items == []
        assert cart.subtotal == Decimal("0")
        assert cart.item_count == 0

    @pytest.mark.asyncio
    async def test_add_item_to_empty_cart(self, cart_service):
        """Test adding an item to an empty cart."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=2,
            unit_price=Decimal("1500"),
        )

        assert len(cart.items) == 1
        assert cart.items[0].product_id == product_id
        assert cart.items[0].product_name == "Test Dragon"
        assert cart.items[0].quantity == 2
        assert cart.items[0].unit_price == Decimal("1500")
        assert cart.items[0].total_price == Decimal("3000")
        assert cart.subtotal == Decimal("3000")
        assert cart.item_count == 2

    @pytest.mark.asyncio
    async def test_add_item_increases_quantity_if_exists(self, cart_service):
        """Test adding same product increases quantity."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        # Add first item
        await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=1,
            unit_price=Decimal("1500"),
        )

        # Add same product again
        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=2,
            unit_price=Decimal("1500"),
        )

        assert len(cart.items) == 1
        assert cart.items[0].quantity == 3
        assert cart.items[0].total_price == Decimal("4500")
        assert cart.subtotal == Decimal("4500")
        assert cart.item_count == 3

    @pytest.mark.asyncio
    async def test_add_multiple_different_items(self, cart_service):
        """Test adding multiple different products."""
        session_id = str(uuid4())
        product_id_1 = str(uuid4())
        product_id_2 = str(uuid4())

        await cart_service.add_item(
            session_id=session_id,
            product_id=product_id_1,
            product_name="Dragon A",
            product_sku="DRG-001",
            quantity=1,
            unit_price=Decimal("1500"),
        )

        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id_2,
            product_name="Dragon B",
            product_sku="DRG-002",
            quantity=2,
            unit_price=Decimal("2000"),
        )

        assert len(cart.items) == 2
        assert cart.subtotal == Decimal("5500")  # 1500 + 4000
        assert cart.item_count == 3  # 1 + 2

    @pytest.mark.asyncio
    async def test_remove_item(self, cart_service):
        """Test removing an item from cart."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=2,
            unit_price=Decimal("1500"),
        )

        item_id = cart.items[0].id

        cart = await cart_service.remove_item(session_id, item_id)

        assert len(cart.items) == 0
        assert cart.subtotal == Decimal("0")
        assert cart.item_count == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_item(self, cart_service):
        """Test removing item that doesn't exist."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=1,
            unit_price=Decimal("1500"),
        )

        # Try to remove non-existent item
        cart = await cart_service.remove_item(session_id, "nonexistent-id")

        # Cart should still have the original item
        assert len(cart.items) == 1

    @pytest.mark.asyncio
    async def test_update_item_quantity(self, cart_service):
        """Test updating item quantity."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=1,
            unit_price=Decimal("1500"),
        )

        item_id = cart.items[0].id

        cart = await cart_service.update_item(session_id, item_id, quantity=5)

        assert cart.items[0].quantity == 5
        assert cart.items[0].total_price == Decimal("7500")
        assert cart.subtotal == Decimal("7500")
        assert cart.item_count == 5

    @pytest.mark.asyncio
    async def test_update_item_quantity_to_zero_removes(self, cart_service):
        """Test updating quantity to 0 removes the item."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=2,
            unit_price=Decimal("1500"),
        )

        item_id = cart.items[0].id

        cart = await cart_service.update_item(session_id, item_id, quantity=0)

        assert len(cart.items) == 0
        assert cart.subtotal == Decimal("0")
        assert cart.item_count == 0

    @pytest.mark.asyncio
    async def test_update_item_negative_quantity_removes(self, cart_service):
        """Test updating to negative quantity removes the item."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=2,
            unit_price=Decimal("1500"),
        )

        item_id = cart.items[0].id

        cart = await cart_service.update_item(session_id, item_id, quantity=-1)

        assert len(cart.items) == 0

    @pytest.mark.asyncio
    async def test_clear_cart(self, cart_service, fake_redis):
        """Test clearing a cart."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=2,
            unit_price=Decimal("1500"),
        )

        # Verify cart exists
        cart = await cart_service.get_cart(session_id)
        assert len(cart.items) == 1

        # Clear cart
        await cart_service.clear_cart(session_id)

        # Get cart again - should be empty
        cart = await cart_service.get_cart(session_id)
        assert len(cart.items) == 0

    @pytest.mark.asyncio
    async def test_cart_persistence(self, cart_service):
        """Test that cart is persisted across get calls."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=3,
            unit_price=Decimal("1500"),
        )

        # Get cart again
        cart = await cart_service.get_cart(session_id)

        assert len(cart.items) == 1
        assert cart.items[0].quantity == 3
        assert cart.subtotal == Decimal("4500")

    @pytest.mark.asyncio
    async def test_add_item_with_image_url(self, cart_service):
        """Test adding item with image URL."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Dragon",
            product_sku="DRG-001",
            quantity=1,
            unit_price=Decimal("1500"),
            image_url="https://example.com/dragon.jpg",
        )

        assert cart.items[0].image_url == "https://example.com/dragon.jpg"

    @pytest.mark.asyncio
    async def test_decimal_precision(self, cart_service):
        """Test that decimal precision is preserved."""
        session_id = str(uuid4())
        product_id = str(uuid4())

        cart = await cart_service.add_item(
            session_id=session_id,
            product_id=product_id,
            product_name="Test Item",
            product_sku="TEST-001",
            quantity=3,
            unit_price=Decimal("1999.99"),
        )

        # Verify precision is maintained
        assert cart.items[0].unit_price == Decimal("1999.99")
        assert cart.items[0].total_price == Decimal("5999.97")
        assert cart.subtotal == Decimal("5999.97")


class TestCartModel:
    """Tests for Cart and CartItem Pydantic models."""

    def test_cart_item_creation(self):
        """Test CartItem model creation."""
        item = CartItem(
            id="test-id",
            product_id="prod-123",
            product_name="Test Product",
            product_sku="SKU-001",
            quantity=2,
            unit_price=Decimal("1000"),
            total_price=Decimal("2000"),
        )

        assert item.id == "test-id"
        assert item.quantity == 2
        assert item.image_url is None

    def test_cart_creation(self):
        """Test Cart model creation."""
        cart = Cart(session_id="sess-123")

        assert cart.session_id == "sess-123"
        assert cart.items == []
        assert cart.subtotal == Decimal("0")
        assert cart.item_count == 0

    def test_cart_with_items(self):
        """Test Cart model with items."""
        items = [
            CartItem(
                id="item-1",
                product_id="prod-1",
                product_name="Product 1",
                product_sku="SKU-1",
                quantity=1,
                unit_price=Decimal("500"),
                total_price=Decimal("500"),
            ),
            CartItem(
                id="item-2",
                product_id="prod-2",
                product_name="Product 2",
                product_sku="SKU-2",
                quantity=2,
                unit_price=Decimal("750"),
                total_price=Decimal("1500"),
            ),
        ]

        cart = Cart(
            session_id="sess-123",
            items=items,
            subtotal=Decimal("2000"),
            item_count=3,
        )

        assert len(cart.items) == 2
        assert cart.subtotal == Decimal("2000")
        assert cart.item_count == 3
