"""Redis caching service for application-wide caching.

Provides a simple interface for caching with TTL, pattern invalidation,
and a decorator for caching function results.
"""

import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional, TypeVar, ParamSpec

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Type variables for decorator
P = ParamSpec("P")
R = TypeVar("R")

# Default TTL values (in seconds)
DEFAULT_TTL = 300  # 5 minutes
PRODUCT_CATALOG_TTL = 300  # 5 minutes
CATEGORY_TTL = 600  # 10 minutes
COST_CALCULATION_TTL = 3600  # 1 hour
DASHBOARD_TTL = 60  # 1 minute

# Cache key prefixes for organization and invalidation
CACHE_PREFIX = "nozzly:cache"
PRODUCT_PREFIX = f"{CACHE_PREFIX}:product"
CATEGORY_PREFIX = f"{CACHE_PREFIX}:category"
DASHBOARD_PREFIX = f"{CACHE_PREFIX}:dashboard"
COST_PREFIX = f"{CACHE_PREFIX}:cost"


class CacheService:
    """
    Redis-based caching service with TTL support.

    Provides methods for:
    - Getting/setting cached values
    - Deleting specific keys
    - Deleting keys by pattern (for invalidation)
    - Decorator for caching function results
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize the cache service.

        Args:
            redis_client: Optional Redis client (for testing)
        """
        self._redis = redis_client
        self._enabled = settings.cache_enabled

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)

    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if not self._enabled:
            return None

        try:
            client = await self._get_redis()
            value = await client.get(key)
            if value is not None:
                return self._deserialize(value)
            return None
        except redis.RedisError as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """
        Set a cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (default 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled:
            return False

        try:
            client = await self._get_redis()
            serialized = self._serialize(value)
            await client.setex(key, ttl, serialized)
            return True
        except redis.RedisError as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a cached value.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False otherwise
        """
        if not self._enabled:
            return False

        try:
            client = await self._get_redis()
            result = await client.delete(key)
            return result > 0
        except redis.RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Useful for cache invalidation when related data changes.

        Args:
            pattern: Redis pattern (e.g., "nozzly:cache:product:*")

        Returns:
            Number of keys deleted
        """
        if not self._enabled:
            return 0

        try:
            client = await self._get_redis()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await client.delete(*keys)
            return 0
        except redis.RedisError as e:
            logger.warning(f"Cache delete_pattern error for pattern {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self._enabled:
            return False

        try:
            client = await self._get_redis()
            return await client.exists(key) > 0
        except redis.RedisError as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist
        """
        if not self._enabled:
            return -2

        try:
            client = await self._get_redis()
            return await client.ttl(key)
        except redis.RedisError as e:
            logger.warning(f"Cache ttl error for key {key}: {e}")
            return -2

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    # Convenience methods for specific cache types

    async def get_product(self, product_id: str, tenant_id: str) -> Optional[dict]:
        """Get cached product data."""
        key = f"{PRODUCT_PREFIX}:{tenant_id}:{product_id}"
        return await self.get(key)

    async def set_product(self, product_id: str, tenant_id: str, data: dict) -> bool:
        """Cache product data."""
        key = f"{PRODUCT_PREFIX}:{tenant_id}:{product_id}"
        return await self.set(key, data, PRODUCT_CATALOG_TTL)

    async def invalidate_product(self, product_id: str, tenant_id: str) -> int:
        """Invalidate product cache."""
        pattern = f"{PRODUCT_PREFIX}:{tenant_id}:{product_id}"
        return await self.delete_pattern(f"{pattern}*")

    async def invalidate_tenant_products(self, tenant_id: str) -> int:
        """Invalidate all products for a tenant."""
        pattern = f"{PRODUCT_PREFIX}:{tenant_id}:*"
        return await self.delete_pattern(pattern)

    async def get_categories(self, tenant_id: str) -> Optional[list]:
        """Get cached categories."""
        key = f"{CATEGORY_PREFIX}:{tenant_id}:all"
        return await self.get(key)

    async def set_categories(self, tenant_id: str, data: list) -> bool:
        """Cache categories."""
        key = f"{CATEGORY_PREFIX}:{tenant_id}:all"
        return await self.set(key, data, CATEGORY_TTL)

    async def invalidate_categories(self, tenant_id: str) -> int:
        """Invalidate category cache."""
        pattern = f"{CATEGORY_PREFIX}:{tenant_id}:*"
        return await self.delete_pattern(pattern)

    async def get_dashboard(self, tenant_id: str, metric: str) -> Optional[Any]:
        """Get cached dashboard metric."""
        key = f"{DASHBOARD_PREFIX}:{tenant_id}:{metric}"
        return await self.get(key)

    async def set_dashboard(self, tenant_id: str, metric: str, data: Any) -> bool:
        """Cache dashboard metric."""
        key = f"{DASHBOARD_PREFIX}:{tenant_id}:{metric}"
        return await self.set(key, data, DASHBOARD_TTL)

    async def invalidate_dashboard(self, tenant_id: str) -> int:
        """Invalidate dashboard cache."""
        pattern = f"{DASHBOARD_PREFIX}:{tenant_id}:*"
        return await self.delete_pattern(pattern)

    async def get_cost_breakdown(self, product_id: str, tenant_id: str) -> Optional[dict]:
        """Get cached cost breakdown."""
        key = f"{COST_PREFIX}:{tenant_id}:{product_id}"
        return await self.get(key)

    async def set_cost_breakdown(self, product_id: str, tenant_id: str, data: dict) -> bool:
        """Cache cost breakdown."""
        key = f"{COST_PREFIX}:{tenant_id}:{product_id}"
        return await self.set(key, data, COST_CALCULATION_TTL)

    async def invalidate_cost(self, tenant_id: str) -> int:
        """Invalidate all cost calculations for a tenant."""
        pattern = f"{COST_PREFIX}:{tenant_id}:*"
        return await self.delete_pattern(pattern)


def build_cache_key(*args, **kwargs) -> str:
    """
    Build a cache key from function arguments.

    Creates a hash of the arguments to ensure unique keys.
    """
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(
    prefix: str,
    ttl: int = DEFAULT_TTL,
    key_builder: Optional[Callable[..., str]] = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to cache function results.

    Usage:
        @cached("product_list", ttl=300)
        async def get_products(tenant_id: str):
            ...

    Args:
        prefix: Cache key prefix (e.g., "product_list")
        ttl: Time-to-live in seconds
        key_builder: Optional function to build cache key from args

    Returns:
        Decorated function
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Skip caching if disabled
            if not settings.cache_enabled:
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
            else:
                key_suffix = build_cache_key(*args, **kwargs)

            cache_key = f"{CACHE_PREFIX}:{prefix}:{key_suffix}"

            # Try to get from cache
            cache = CacheService()
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_value
            except Exception as e:
                logger.warning(f"Cache read error: {e}")

            # Call function and cache result
            result = await func(*args, **kwargs)

            try:
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {cache_key}")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")

            return result

        return wrapper

    return decorator


# Singleton instance for use across the application
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get or create the cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


async def invalidate_on_product_change(tenant_id: str, product_id: str) -> None:
    """
    Invalidate all caches related to a product change.

    Call this when a product is created, updated, or deleted.
    """
    cache = await get_cache_service()
    await cache.invalidate_product(product_id, tenant_id)
    await cache.invalidate_cost(tenant_id)
    await cache.invalidate_dashboard(tenant_id)


async def invalidate_on_order_complete(tenant_id: str) -> None:
    """
    Invalidate caches after an order is completed.

    Call this when an order is placed or fulfilled.
    """
    cache = await get_cache_service()
    await cache.invalidate_dashboard(tenant_id)


async def invalidate_on_inventory_change(tenant_id: str) -> None:
    """
    Invalidate caches after inventory changes.

    Call this when stock levels change.
    """
    cache = await get_cache_service()
    await cache.invalidate_tenant_products(tenant_id)
    await cache.invalidate_dashboard(tenant_id)
