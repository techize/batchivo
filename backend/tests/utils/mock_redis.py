"""
Mock Redis implementation for testing.

Provides a MockRedis class that simulates Redis behavior including
Lua script support (register_script/evalsha) which fakeredis doesn't support.

Usage:
    from tests.utils.mock_redis import MockRedis

    mock_redis = MockRedis()
    service = StockReservationService(redis_client=mock_redis)
"""


class MockScript:
    """Mock Redis Lua script for testing.

    Simulates the RESERVE_SCRIPT behavior from StockReservationService.
    """

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
        """Execute all queued commands."""
        for cmd in self.commands:
            if cmd[0] == "hset":
                key, args, kwargs = cmd[1], cmd[2], cmd[3]
                if key not in self.redis.data:
                    self.redis.data[key] = {}
                if "mapping" in kwargs:
                    self.redis.data[key].update(kwargs["mapping"])
                elif args:
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
        self.commands = []


class MockRedis:
    """
    Mock Redis client for testing.

    Supports:
    - Basic hash operations (hget, hset, hgetall, hdel)
    - Key operations (get, set, setex, delete, exists, expire)
    - Pipelines
    - Lua script simulation via register_script

    This is used instead of fakeredis for tests that require
    Lua script support (evalsha), which fakeredis doesn't implement.
    """

    def __init__(self):
        self.data = {}
        self.ttls = {}

    def register_script(self, script):
        """Register a Lua script and return a callable MockScript."""
        return MockScript(self, script)

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        self.data[key] = value
        if ex:
            self.ttls[key] = ex

    async def setex(self, key, ttl, value):
        self.data[key] = value
        self.ttls[key] = ttl

    async def hget(self, key, field):
        return self.data.get(key, {}).get(field)

    async def hgetall(self, key):
        return self.data.get(key, {})

    async def hset(self, key, *args, **kwargs):
        if key not in self.data:
            self.data[key] = {}
        if "mapping" in kwargs:
            self.data[key].update(kwargs["mapping"])
        elif args:
            # Handle hset(key, field, value)
            self.data[key][args[0]] = args[1]

    async def hdel(self, key, field):
        if key in self.data and field in self.data[key]:
            del self.data[key][field]

    async def delete(self, *keys):
        for key in keys:
            if key in self.data:
                del self.data[key]

    async def exists(self, key):
        return 1 if key in self.data else 0

    async def expire(self, key, ttl):
        self.ttls[key] = ttl

    async def keys(self, pattern="*"):
        """Simple pattern matching for keys."""
        import fnmatch

        return [k for k in self.data.keys() if fnmatch.fnmatch(k, pattern)]

    def pipeline(self):
        return MockPipeline(self)

    async def close(self):
        pass
