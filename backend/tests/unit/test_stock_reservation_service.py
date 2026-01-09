"""
Unit tests for StockReservationService.
"""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.stock_reservation import (
    StockReservationService,
    ReservationItem,
)


class MockScript:
    """Mock Redis Lua script for testing."""

    def __init__(self, redis, script):
        self.redis = redis
        self.script = script

    async def __call__(self, keys=None, args=None):
        """
        Simulate the RESERVE_SCRIPT Lua script behavior.

        The script atomically checks availability and reserves stock.
        Returns 1 if successful, 0 if insufficient stock.
        """
        keys = keys or []
        args = args or []

        product_key = keys[0] if len(keys) > 0 else None
        session_key = keys[1] if len(keys) > 1 else None
        session_id = args[0] if len(args) > 0 else None
        product_id = args[1] if len(args) > 1 else None
        quantity = int(args[2]) if len(args) > 2 else 0
        max_available = int(args[3]) if len(args) > 3 else 0
        reservation_data = args[4] if len(args) > 4 else "{}"
        ttl = int(args[5]) if len(args) > 5 else 900

        # Get current total reserved for this product
        reservations = self.redis.data.get(product_key, {})
        total_reserved = sum(int(qty) for qty in reservations.values())

        # Check availability
        available = max_available - total_reserved
        if available < quantity:
            return 0  # Insufficient stock

        # Atomically add reservations
        if product_key not in self.redis.data:
            self.redis.data[product_key] = {}
        self.redis.data[product_key][session_id] = str(quantity)
        self.redis.ttls[product_key] = ttl

        if session_key not in self.redis.data:
            self.redis.data[session_key] = {}
        self.redis.data[session_key][product_id] = reservation_data
        self.redis.ttls[session_key] = ttl

        return 1  # Success


class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self):
        self.data = {}
        self.ttls = {}

    def register_script(self, script):
        """Register a Lua script and return a callable."""
        return MockScript(self, script)

    async def get(self, key):
        return self.data.get(key)

    async def hgetall(self, key):
        return self.data.get(key, {})

    async def hset(self, key, *args, **kwargs):
        if key not in self.data:
            self.data[key] = {}
        if "mapping" in kwargs:
            self.data[key].update(kwargs["mapping"])
        else:
            # Handle hset(key, field, value)
            self.data[key][args[0]] = args[1]

    async def hdel(self, key, field):
        if key in self.data and field in self.data[key]:
            del self.data[key][field]

    async def delete(self, key):
        if key in self.data:
            del self.data[key]

    async def exists(self, key):
        return 1 if key in self.data else 0

    async def expire(self, key, ttl):
        self.ttls[key] = ttl

    async def setex(self, key, ttl, value):
        self.data[key] = value
        self.ttls[key] = ttl

    def pipeline(self):
        return MockPipeline(self)

    async def close(self):
        pass


class MockPipeline:
    """Mock Redis pipeline for testing."""

    def __init__(self, redis):
        self.redis = redis
        self.commands = []

    def hset(self, key, *args, **kwargs):
        self.commands.append(("hset", key, args, kwargs))
        return self

    def hdel(self, key, field):
        self.commands.append(("hdel", key, field))
        return self

    def delete(self, key):
        self.commands.append(("delete", key))
        return self

    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))
        return self

    async def execute(self):
        for cmd in self.commands:
            if cmd[0] == "hset":
                key, args, kwargs = cmd[1], cmd[2], cmd[3]
                if key not in self.redis.data:
                    self.redis.data[key] = {}
                if "mapping" in kwargs:
                    self.redis.data[key].update(kwargs["mapping"])
                elif len(args) >= 2:
                    self.redis.data[key][args[0]] = args[1]
            elif cmd[0] == "hdel":
                key, field = cmd[1], cmd[2]
                if key in self.redis.data and field in self.redis.data[key]:
                    del self.redis.data[key][field]
            elif cmd[0] == "delete":
                key = cmd[1]
                if key in self.redis.data:
                    del self.redis.data[key]
            elif cmd[0] == "expire":
                key, ttl = cmd[1], cmd[2]
                self.redis.ttls[key] = ttl
        return [True] * len(self.commands)


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    return MockRedis()


@pytest.fixture
def reservation_service(mock_redis):
    """Create reservation service with mock Redis."""
    service = StockReservationService(redis_client=mock_redis, ttl=900)
    return service


class TestStockReservationService:
    """Tests for StockReservationService."""

    @pytest.mark.asyncio
    async def test_reserve_stock_success(self, reservation_service, mock_redis):
        """Test successful stock reservation."""
        session_id = "test-session-123"
        product_id = str(uuid4())

        items = [
            ReservationItem(
                product_id=product_id,
                quantity=2,
                product_name="Test Product",
                product_sku="TEST-001",
            )
        ]

        # Mock database session and product
        mock_db = AsyncMock()
        mock_product = MagicMock()
        mock_product.units_in_stock = 10
        mock_product.name = "Test Product"
        mock_product.sku = "TEST-001"
        mock_product.print_to_order = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_db.execute.return_value = mock_result

        result = await reservation_service.reserve_stock(session_id, items, mock_db)

        assert result.success is True
        assert result.session_id == session_id
        assert len(result.reserved_items) == 1
        assert len(result.failed_items) == 0
        assert result.reserved_items[0].product_id == product_id
        assert result.reserved_items[0].quantity == 2

    @pytest.mark.asyncio
    async def test_reserve_stock_insufficient_inventory(self, reservation_service):
        """Test reservation fails when insufficient stock."""
        session_id = "test-session-456"
        product_id = str(uuid4())

        items = [
            ReservationItem(
                product_id=product_id,
                quantity=10,
                product_name="Test Product",
                product_sku="TEST-001",
            )
        ]

        # Mock database session and product with low stock
        mock_db = AsyncMock()
        mock_product = MagicMock()
        mock_product.units_in_stock = 5
        mock_product.name = "Test Product"
        mock_product.sku = "TEST-001"
        mock_product.print_to_order = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_db.execute.return_value = mock_result

        result = await reservation_service.reserve_stock(session_id, items, mock_db)

        assert result.success is False
        assert len(result.reserved_items) == 0
        assert len(result.failed_items) == 1
        assert result.failed_items[0]["reason"] == "Insufficient stock"
        assert result.failed_items[0]["available"] == 5
        assert result.failed_items[0]["requested"] == 10

    @pytest.mark.asyncio
    async def test_reserve_stock_print_to_order_always_succeeds(self, reservation_service):
        """Test print-to-order products can always be reserved."""
        session_id = "test-session-789"
        product_id = str(uuid4())

        items = [
            ReservationItem(
                product_id=product_id,
                quantity=100,  # High quantity
                product_name="Print to Order Product",
                product_sku="PTO-001",
            )
        ]

        # Mock database session and print-to-order product
        mock_db = AsyncMock()
        mock_product = MagicMock()
        mock_product.units_in_stock = 0  # No stock
        mock_product.name = "Print to Order Product"
        mock_product.sku = "PTO-001"
        mock_product.print_to_order = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_db.execute.return_value = mock_result

        result = await reservation_service.reserve_stock(session_id, items, mock_db)

        assert result.success is True
        assert len(result.reserved_items) == 1

    @pytest.mark.asyncio
    async def test_reserve_stock_product_not_found(self, reservation_service):
        """Test reservation fails when product not found."""
        session_id = "test-session-notfound"
        product_id = str(uuid4())

        items = [
            ReservationItem(
                product_id=product_id,
                quantity=1,
            )
        ]

        # Mock database session with no product
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await reservation_service.reserve_stock(session_id, items, mock_db)

        assert result.success is False
        assert len(result.failed_items) == 1
        assert result.failed_items[0]["reason"] == "Product not found"

    @pytest.mark.asyncio
    async def test_release_reservation(self, reservation_service, mock_redis):
        """Test releasing a reservation."""
        session_id = "test-session-release"
        product_id = str(uuid4())

        # Set up existing reservation
        session_key = f"reservation:{session_id}"
        product_key = f"product_reservations:{product_id}"

        mock_redis.data[session_key] = {
            product_id: json.dumps(
                {
                    "quantity": 5,
                    "product_name": "Test",
                    "product_sku": "TEST",
                }
            )
        }
        mock_redis.data[product_key] = {session_id: "5"}

        result = await reservation_service.release_reservation(session_id)

        assert result is True
        assert session_key not in mock_redis.data
        # Product key should have session removed
        assert session_id not in mock_redis.data.get(product_key, {})

    @pytest.mark.asyncio
    async def test_release_nonexistent_reservation(self, reservation_service, mock_redis):
        """Test releasing non-existent reservation returns False."""
        result = await reservation_service.release_reservation("nonexistent-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_reserved_quantity(self, reservation_service, mock_redis):
        """Test getting total reserved quantity for a product."""
        product_id = str(uuid4())
        product_key = f"product_reservations:{product_id}"

        # Set up reservations from multiple sessions
        mock_redis.data[product_key] = {
            "session-1": "3",
            "session-2": "5",
            "session-3": "2",
        }

        total = await reservation_service.get_reserved_quantity(product_id)
        assert total == 10

    @pytest.mark.asyncio
    async def test_get_reserved_quantity_no_reservations(self, reservation_service, mock_redis):
        """Test getting reserved quantity when none exist."""
        product_id = str(uuid4())
        total = await reservation_service.get_reserved_quantity(product_id)
        assert total == 0

    @pytest.mark.asyncio
    async def test_get_available_stock(self, reservation_service, mock_redis):
        """Test getting available stock (total minus reserved)."""
        product_id = str(uuid4())
        product_key = f"product_reservations:{product_id}"

        # Set up reservations
        mock_redis.data[product_key] = {
            "session-1": "3",
            "session-2": "2",
        }

        # Mock database
        mock_db = AsyncMock()
        mock_product = MagicMock()
        mock_product.units_in_stock = 10

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_db.execute.return_value = mock_result

        stock_info = await reservation_service.get_available_stock(product_id, mock_db)

        assert stock_info.product_id == product_id
        assert stock_info.total_stock == 10
        assert stock_info.reserved_stock == 5
        assert stock_info.available_stock == 5

    @pytest.mark.asyncio
    async def test_confirm_reservation(self, reservation_service, mock_redis):
        """Test confirming a reservation (releases it)."""
        session_id = "test-session-confirm"
        product_id = str(uuid4())

        # Set up existing reservation
        session_key = f"reservation:{session_id}"
        product_key = f"product_reservations:{product_id}"

        mock_redis.data[session_key] = {product_id: json.dumps({"quantity": 3})}
        mock_redis.data[product_key] = {session_id: "3"}

        result = await reservation_service.confirm_reservation(session_id)

        assert result is True
        assert session_key not in mock_redis.data

    @pytest.mark.asyncio
    async def test_get_session_reservations(self, reservation_service, mock_redis):
        """Test getting all reservations for a session."""
        session_id = "test-session-get"
        product_id_1 = str(uuid4())
        product_id_2 = str(uuid4())

        session_key = f"reservation:{session_id}"
        mock_redis.data[session_key] = {
            product_id_1: json.dumps(
                {
                    "quantity": 2,
                    "product_name": "Product 1",
                    "product_sku": "P1",
                }
            ),
            product_id_2: json.dumps(
                {
                    "quantity": 3,
                    "product_name": "Product 2",
                    "product_sku": "P2",
                }
            ),
        }

        items = await reservation_service.get_session_reservations(session_id)

        assert len(items) == 2
        product_ids = {item.product_id for item in items}
        assert product_id_1 in product_ids
        assert product_id_2 in product_ids

    @pytest.mark.asyncio
    async def test_extend_reservation(self, reservation_service, mock_redis):
        """Test extending reservation TTL."""
        session_id = "test-session-extend"
        product_id = str(uuid4())

        session_key = f"reservation:{session_id}"
        product_key = f"product_reservations:{product_id}"

        mock_redis.data[session_key] = {product_id: json.dumps({"quantity": 1})}
        mock_redis.data[product_key] = {session_id: "1"}

        result = await reservation_service.extend_reservation(session_id)

        assert result is True
        # Check TTL was set
        assert session_key in mock_redis.ttls
        assert mock_redis.ttls[session_key] == 900  # Default TTL

    @pytest.mark.asyncio
    async def test_extend_nonexistent_reservation(self, reservation_service, mock_redis):
        """Test extending non-existent reservation returns False."""
        result = await reservation_service.extend_reservation("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_reserve_replaces_existing_reservation(self, reservation_service, mock_redis):
        """Test that new reservation replaces existing one for same session."""
        session_id = "test-session-replace"
        product_id = str(uuid4())

        # Set up existing reservation
        session_key = f"reservation:{session_id}"
        mock_redis.data[session_key] = {"old-product": json.dumps({"quantity": 5})}

        items = [
            ReservationItem(
                product_id=product_id,
                quantity=2,
                product_name="New Product",
                product_sku="NEW-001",
            )
        ]

        # Mock database
        mock_db = AsyncMock()
        mock_product = MagicMock()
        mock_product.units_in_stock = 10
        mock_product.name = "New Product"
        mock_product.sku = "NEW-001"
        mock_product.print_to_order = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_product
        mock_db.execute.return_value = mock_result

        result = await reservation_service.reserve_stock(session_id, items, mock_db)

        assert result.success is True
        # Old product should be removed, new product should be present
        assert "old-product" not in mock_redis.data.get(session_key, {})

    @pytest.mark.asyncio
    async def test_all_or_nothing_reservation(self, reservation_service):
        """Test that if one item fails, no items are reserved."""
        session_id = "test-session-allornone"
        product_id_1 = str(uuid4())
        product_id_2 = str(uuid4())

        items = [
            ReservationItem(product_id=product_id_1, quantity=2),  # Will succeed
            ReservationItem(product_id=product_id_2, quantity=100),  # Will fail
        ]

        # Mock database
        mock_db = AsyncMock()

        def mock_execute(query):
            result = MagicMock()
            product = MagicMock()
            product.name = "Test Product"
            product.sku = "TEST"
            product.print_to_order = False

            # Check which product is being queried
            query_str = str(query)
            if product_id_1 in query_str:
                product.units_in_stock = 10
            else:
                product.units_in_stock = 5  # Not enough for 100

            result.scalar_one_or_none.return_value = product
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        result = await reservation_service.reserve_stock(session_id, items, mock_db)

        assert result.success is False
        assert len(result.reserved_items) == 0  # Nothing reserved
        assert len(result.failed_items) == 1  # One failure
