"""Unit tests for the cache service."""

import pytest
from unittest.mock import patch

import fakeredis.aioredis

from app.services.cache_service import (
    CacheService,
    build_cache_key,
    invalidate_on_product_change,
    invalidate_on_order_complete,
    invalidate_on_inventory_change,
)


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client for testing."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def cache_service(fake_redis):
    """Create a cache service with fake Redis."""
    return CacheService(redis_client=fake_redis)


class TestCacheService:
    """Tests for CacheService."""

    async def test_set_and_get(self, cache_service):
        """Test basic set and get operations."""
        await cache_service.set("test:key", {"foo": "bar"})
        result = await cache_service.get("test:key")

        assert result == {"foo": "bar"}

    async def test_get_nonexistent_key(self, cache_service):
        """Test getting a nonexistent key returns None."""
        result = await cache_service.get("nonexistent:key")
        assert result is None

    async def test_set_with_ttl(self, cache_service):
        """Test setting with TTL."""
        await cache_service.set("test:ttl", "value", ttl=60)
        ttl = await cache_service.get_ttl("test:ttl")

        assert ttl > 0
        assert ttl <= 60

    async def test_delete(self, cache_service):
        """Test deleting a key."""
        await cache_service.set("test:delete", "value")
        deleted = await cache_service.delete("test:delete")

        assert deleted is True
        result = await cache_service.get("test:delete")
        assert result is None

    async def test_delete_nonexistent(self, cache_service):
        """Test deleting a nonexistent key."""
        deleted = await cache_service.delete("nonexistent:key")
        assert deleted is False

    async def test_delete_pattern(self, cache_service):
        """Test deleting keys by pattern."""
        await cache_service.set("test:pattern:1", "value1")
        await cache_service.set("test:pattern:2", "value2")
        await cache_service.set("test:other:1", "value3")

        deleted = await cache_service.delete_pattern("test:pattern:*")

        assert deleted == 2
        assert await cache_service.get("test:pattern:1") is None
        assert await cache_service.get("test:pattern:2") is None
        assert await cache_service.get("test:other:1") == "value3"

    async def test_exists(self, cache_service):
        """Test checking if key exists."""
        await cache_service.set("test:exists", "value")

        assert await cache_service.exists("test:exists") is True
        assert await cache_service.exists("nonexistent") is False

    async def test_serialize_complex_types(self, cache_service):
        """Test serialization of complex types."""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "list": [1, 2, 3],
            "nested": {"a": 1, "b": 2},
        }
        await cache_service.set("test:complex", data)
        result = await cache_service.get("test:complex")

        assert result == data


class TestProductCaching:
    """Tests for product-specific caching methods."""

    async def test_set_and_get_product(self, cache_service):
        """Test product caching."""
        product_data = {"id": "123", "name": "Test Product", "price": 19.99}
        await cache_service.set_product("123", "tenant1", product_data)
        result = await cache_service.get_product("123", "tenant1")

        assert result == product_data

    async def test_invalidate_product(self, cache_service):
        """Test product cache invalidation."""
        await cache_service.set_product("123", "tenant1", {"name": "Product"})
        await cache_service.invalidate_product("123", "tenant1")

        result = await cache_service.get_product("123", "tenant1")
        assert result is None

    async def test_invalidate_tenant_products(self, cache_service):
        """Test invalidating all products for a tenant."""
        await cache_service.set_product("1", "tenant1", {"name": "Product 1"})
        await cache_service.set_product("2", "tenant1", {"name": "Product 2"})
        await cache_service.set_product("3", "tenant2", {"name": "Product 3"})

        await cache_service.invalidate_tenant_products("tenant1")

        assert await cache_service.get_product("1", "tenant1") is None
        assert await cache_service.get_product("2", "tenant1") is None
        assert await cache_service.get_product("3", "tenant2") is not None


class TestCategoryCaching:
    """Tests for category-specific caching methods."""

    async def test_set_and_get_categories(self, cache_service):
        """Test category caching."""
        categories = [{"id": "1", "name": "Dragons"}, {"id": "2", "name": "Animals"}]
        await cache_service.set_categories("tenant1", categories)
        result = await cache_service.get_categories("tenant1")

        assert result == categories

    async def test_invalidate_categories(self, cache_service):
        """Test category cache invalidation."""
        await cache_service.set_categories("tenant1", [{"id": "1", "name": "Test"}])
        await cache_service.invalidate_categories("tenant1")

        result = await cache_service.get_categories("tenant1")
        assert result is None


class TestDashboardCaching:
    """Tests for dashboard-specific caching methods."""

    async def test_set_and_get_dashboard(self, cache_service):
        """Test dashboard metric caching."""
        await cache_service.set_dashboard("tenant1", "total_sales", 12345.67)
        result = await cache_service.get_dashboard("tenant1", "total_sales")

        assert result == 12345.67

    async def test_invalidate_dashboard(self, cache_service):
        """Test dashboard cache invalidation."""
        await cache_service.set_dashboard("tenant1", "metric1", 100)
        await cache_service.set_dashboard("tenant1", "metric2", 200)
        await cache_service.invalidate_dashboard("tenant1")

        assert await cache_service.get_dashboard("tenant1", "metric1") is None
        assert await cache_service.get_dashboard("tenant1", "metric2") is None


class TestCostCaching:
    """Tests for cost calculation caching."""

    async def test_set_and_get_cost_breakdown(self, cache_service):
        """Test cost breakdown caching."""
        cost_data = {"materials": 5.00, "labor": 3.00, "total": 8.00}
        await cache_service.set_cost_breakdown("123", "tenant1", cost_data)
        result = await cache_service.get_cost_breakdown("123", "tenant1")

        assert result == cost_data

    async def test_invalidate_cost(self, cache_service):
        """Test cost cache invalidation."""
        await cache_service.set_cost_breakdown("1", "tenant1", {"total": 10})
        await cache_service.set_cost_breakdown("2", "tenant1", {"total": 20})
        await cache_service.invalidate_cost("tenant1")

        assert await cache_service.get_cost_breakdown("1", "tenant1") is None
        assert await cache_service.get_cost_breakdown("2", "tenant1") is None


class TestBuildCacheKey:
    """Tests for cache key builder."""

    def test_build_key_from_args(self):
        """Test building cache key from positional arguments."""
        key1 = build_cache_key("arg1", "arg2")
        key2 = build_cache_key("arg1", "arg2")
        key3 = build_cache_key("arg1", "arg3")

        assert key1 == key2
        assert key1 != key3

    def test_build_key_from_kwargs(self):
        """Test building cache key from keyword arguments."""
        key1 = build_cache_key(a=1, b=2)
        key2 = build_cache_key(b=2, a=1)  # Order shouldn't matter
        key3 = build_cache_key(a=1, b=3)

        assert key1 == key2
        assert key1 != key3

    def test_build_key_mixed_args(self):
        """Test building cache key from mixed arguments."""
        key = build_cache_key("pos1", "pos2", key1="val1", key2="val2")
        assert len(key) == 32  # MD5 hash length


class TestCacheDisabled:
    """Tests for behavior when caching is disabled."""

    async def test_operations_when_disabled(self, fake_redis):
        """Test that operations are no-ops when caching is disabled."""
        with patch("app.services.cache_service.settings") as mock_settings:
            mock_settings.cache_enabled = False

            cache = CacheService(redis_client=fake_redis)

            # All operations should return appropriate "disabled" values
            result = await cache.get("key")
            assert result is None

            success = await cache.set("key", "value")
            assert success is False

            deleted = await cache.delete("key")
            assert deleted is False

            exists = await cache.exists("key")
            assert exists is False


class TestInvalidationHelpers:
    """Tests for invalidation helper functions."""

    async def test_invalidate_on_product_change(self, fake_redis):
        """Test product change invalidation."""
        cache = CacheService(redis_client=fake_redis)

        # Set up some cached data
        await cache.set_product("prod1", "tenant1", {"name": "Product"})
        await cache.set_cost_breakdown("prod1", "tenant1", {"total": 10})
        await cache.set_dashboard("tenant1", "metric", 100)

        # Mock the get_cache_service to return our test cache
        with patch("app.services.cache_service._cache_service", cache):
            await invalidate_on_product_change("tenant1", "prod1")

        # All should be invalidated
        assert await cache.get_product("prod1", "tenant1") is None
        assert await cache.get_cost_breakdown("prod1", "tenant1") is None
        assert await cache.get_dashboard("tenant1", "metric") is None

    async def test_invalidate_on_order_complete(self, fake_redis):
        """Test order completion invalidation."""
        cache = CacheService(redis_client=fake_redis)

        await cache.set_dashboard("tenant1", "order_count", 50)

        with patch("app.services.cache_service._cache_service", cache):
            await invalidate_on_order_complete("tenant1")

        assert await cache.get_dashboard("tenant1", "order_count") is None

    async def test_invalidate_on_inventory_change(self, fake_redis):
        """Test inventory change invalidation."""
        cache = CacheService(redis_client=fake_redis)

        await cache.set_product("prod1", "tenant1", {"stock": 10})
        await cache.set_dashboard("tenant1", "low_stock", 5)

        with patch("app.services.cache_service._cache_service", cache):
            await invalidate_on_inventory_change("tenant1")

        assert await cache.get_product("prod1", "tenant1") is None
        assert await cache.get_dashboard("tenant1", "low_stock") is None
