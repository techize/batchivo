"""
Tests for Redis-backed checkout session service.
"""

import pytest
from decimal import Decimal
from uuid import uuid4

import fakeredis.aioredis
from app.services.checkout_session import CheckoutSessionService, CheckoutSessionData


@pytest.fixture
def fake_redis():
    """Create a fake Redis client for testing."""
    return fakeredis.aioredis.FakeRedis(encoding="utf-8", decode_responses=True)


@pytest.fixture
def checkout_service(fake_redis):
    """Create a checkout session service with fake Redis."""
    return CheckoutSessionService(redis_client=fake_redis, ttl=3600)


class TestCheckoutSessionService:
    """Tests for CheckoutSessionService."""

    @pytest.mark.asyncio
    async def test_create_session(self, checkout_service):
        """Test creating a new checkout session."""
        cart_session_id = str(uuid4())
        shipping_address = {
            "name": "John Doe",
            "email": "john@example.com",
            "line1": "123 Main St",
            "city": "London",
            "postcode": "SW1A 1AA",
        }

        session_id = await checkout_service.create_session(
            cart_session_id=cart_session_id,
            shipping_address=shipping_address,
            shipping_method_id="royal-mail-tracked-24",
            shipping_method_name="Royal Mail Tracked 24",
            subtotal=Decimal("2500"),
            shipping_cost=Decimal("595"),
            total=Decimal("3095"),
        )

        assert session_id is not None
        assert len(session_id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_get_session(self, checkout_service):
        """Test retrieving a checkout session."""
        cart_session_id = str(uuid4())
        shipping_address = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "line1": "456 High St",
            "city": "Manchester",
            "postcode": "M1 1AA",
        }

        session_id = await checkout_service.create_session(
            cart_session_id=cart_session_id,
            shipping_address=shipping_address,
            shipping_method_id="royal-mail-2nd",
            shipping_method_name="Royal Mail 2nd Class",
            subtotal=Decimal("1500"),
            shipping_cost=Decimal("0"),
            total=Decimal("1500"),
        )

        session = await checkout_service.get_session(session_id)

        assert session is not None
        assert session.session_id == session_id
        assert session.cart_session_id == cart_session_id
        assert session.shipping_address == shipping_address
        assert session.shipping_method_id == "royal-mail-2nd"
        assert session.shipping_method_name == "Royal Mail 2nd Class"
        assert session.subtotal == Decimal("1500")
        assert session.shipping_cost == Decimal("0")
        assert session.total == Decimal("1500")
        assert session.created_at is not None

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, checkout_service):
        """Test getting a session that doesn't exist returns None."""
        session = await checkout_service.get_session("nonexistent-session-id")
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_session(self, checkout_service):
        """Test deleting a checkout session."""
        cart_session_id = str(uuid4())
        shipping_address = {"name": "Test", "email": "test@example.com"}

        session_id = await checkout_service.create_session(
            cart_session_id=cart_session_id,
            shipping_address=shipping_address,
            shipping_method_id="standard",
            shipping_method_name="Standard",
            subtotal=Decimal("1000"),
            shipping_cost=Decimal("395"),
            total=Decimal("1395"),
        )

        # Verify session exists
        session = await checkout_service.get_session(session_id)
        assert session is not None

        # Delete session
        await checkout_service.delete_session(session_id)

        # Verify session is gone
        session = await checkout_service.get_session(session_id)
        assert session is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, checkout_service):
        """Test deleting a nonexistent session doesn't raise error."""
        # Should not raise any exception
        await checkout_service.delete_session("nonexistent-session-id")

    @pytest.mark.asyncio
    async def test_decimal_precision(self, checkout_service):
        """Test that decimal precision is preserved."""
        cart_session_id = str(uuid4())
        shipping_address = {"name": "Test", "email": "test@example.com"}

        session_id = await checkout_service.create_session(
            cart_session_id=cart_session_id,
            shipping_address=shipping_address,
            shipping_method_id="standard",
            shipping_method_name="Standard",
            subtotal=Decimal("1999.99"),
            shipping_cost=Decimal("5.95"),
            total=Decimal("2005.94"),
        )

        session = await checkout_service.get_session(session_id)

        assert session.subtotal == Decimal("1999.99")
        assert session.shipping_cost == Decimal("5.95")
        assert session.total == Decimal("2005.94")

    @pytest.mark.asyncio
    async def test_session_persistence(self, checkout_service):
        """Test that session is persisted across get calls."""
        cart_session_id = str(uuid4())
        shipping_address = {
            "name": "Persistent User",
            "email": "persist@example.com",
            "line1": "789 Oak Lane",
            "city": "Birmingham",
            "postcode": "B1 1AA",
        }

        session_id = await checkout_service.create_session(
            cart_session_id=cart_session_id,
            shipping_address=shipping_address,
            shipping_method_id="royal-mail-tracked",
            shipping_method_name="Royal Mail Tracked",
            subtotal=Decimal("5000"),
            shipping_cost=Decimal("595"),
            total=Decimal("5595"),
        )

        # Get session multiple times
        session1 = await checkout_service.get_session(session_id)
        session2 = await checkout_service.get_session(session_id)

        assert session1.session_id == session2.session_id
        assert session1.total == session2.total
        assert session1.shipping_address == session2.shipping_address

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, checkout_service):
        """Test creating multiple independent checkout sessions."""
        session_id_1 = await checkout_service.create_session(
            cart_session_id=str(uuid4()),
            shipping_address={"name": "User 1", "email": "user1@example.com"},
            shipping_method_id="method-1",
            shipping_method_name="Method 1",
            subtotal=Decimal("1000"),
            shipping_cost=Decimal("100"),
            total=Decimal("1100"),
        )

        session_id_2 = await checkout_service.create_session(
            cart_session_id=str(uuid4()),
            shipping_address={"name": "User 2", "email": "user2@example.com"},
            shipping_method_id="method-2",
            shipping_method_name="Method 2",
            subtotal=Decimal("2000"),
            shipping_cost=Decimal("200"),
            total=Decimal("2200"),
        )

        # Verify they are independent
        assert session_id_1 != session_id_2

        session1 = await checkout_service.get_session(session_id_1)
        session2 = await checkout_service.get_session(session_id_2)

        assert session1.total == Decimal("1100")
        assert session2.total == Decimal("2200")
        assert session1.shipping_address["name"] == "User 1"
        assert session2.shipping_address["name"] == "User 2"


class TestCheckoutSessionDataModel:
    """Tests for CheckoutSessionData Pydantic model."""

    def test_model_creation(self):
        """Test CheckoutSessionData model creation."""
        data = CheckoutSessionData(
            session_id="test-session-id",
            cart_session_id="test-cart-id",
            shipping_address={"name": "Test", "email": "test@example.com"},
            shipping_method_id="standard",
            shipping_method_name="Standard Shipping",
            subtotal=Decimal("1000"),
            shipping_cost=Decimal("500"),
            total=Decimal("1500"),
            created_at="2025-12-18T10:00:00Z",
        )

        assert data.session_id == "test-session-id"
        assert data.cart_session_id == "test-cart-id"
        assert data.subtotal == Decimal("1000")
        assert data.shipping_cost == Decimal("500")
        assert data.total == Decimal("1500")

    def test_model_json_serialization(self):
        """Test that model can be serialized to JSON."""
        data = CheckoutSessionData(
            session_id="json-test-id",
            cart_session_id="json-cart-id",
            shipping_address={"name": "JSON Test"},
            shipping_method_id="express",
            shipping_method_name="Express Shipping",
            subtotal=Decimal("2500"),
            shipping_cost=Decimal("1000"),
            total=Decimal("3500"),
            created_at="2025-12-18T12:00:00Z",
        )

        json_str = data.model_dump_json()
        assert "json-test-id" in json_str
        assert "2500" in json_str
