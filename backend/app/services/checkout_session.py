"""
Checkout session service with Redis-backed persistent storage.

Stores checkout session data (shipping address, payment details) persistently
so sessions survive server restarts.
"""

import json
from typing import Optional
from uuid import uuid4
from decimal import Decimal

import redis.asyncio as redis
from pydantic import BaseModel

from app.config import get_settings


class CheckoutSessionData(BaseModel):
    """Checkout session data stored in Redis."""

    session_id: str
    cart_session_id: str
    shipping_address: dict
    shipping_method_id: str
    shipping_method_name: str
    subtotal: Decimal
    shipping_cost: Decimal
    discount_code: Optional[str] = None
    discount_amount: Decimal = Decimal("0")
    total: Decimal
    created_at: str  # ISO timestamp

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class CheckoutSessionService:
    """
    Redis-backed checkout session service.

    Key format: checkout:{session_id}
    TTL: 1 hour (checkout sessions should be short-lived)
    """

    DEFAULT_TTL = 3600  # 1 hour in seconds

    def __init__(self, redis_client: Optional[redis.Redis] = None, ttl: int = DEFAULT_TTL):
        """
        Initialize checkout session service.

        Args:
            redis_client: Optional Redis client (for testing)
            ttl: Session TTL in seconds (default 1 hour)
        """
        self._redis = redis_client
        self._ttl = ttl

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _key(self, session_id: str) -> str:
        """Generate Redis key for checkout session."""
        return f"checkout:{session_id}"

    async def create_session(
        self,
        cart_session_id: str,
        shipping_address: dict,
        shipping_method_id: str,
        shipping_method_name: str,
        subtotal: Decimal,
        shipping_cost: Decimal,
        total: Decimal,
        discount_code: Optional[str] = None,
        discount_amount: Decimal = Decimal("0"),
    ) -> str:
        """
        Create a new checkout session.

        Args:
            cart_session_id: Associated cart session ID
            shipping_address: Customer shipping address
            shipping_method_id: Selected shipping method ID
            shipping_method_name: Shipping method display name
            subtotal: Cart subtotal in pence
            shipping_cost: Shipping cost in pence
            total: Order total in pence
            discount_code: Applied discount code (optional)
            discount_amount: Discount amount in pence (optional)

        Returns:
            New session ID
        """
        from datetime import datetime, timezone

        session_id = str(uuid4())
        session_data = CheckoutSessionData(
            session_id=session_id,
            cart_session_id=cart_session_id,
            shipping_address=shipping_address,
            shipping_method_id=shipping_method_id,
            shipping_method_name=shipping_method_name,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            discount_code=discount_code,
            discount_amount=discount_amount,
            total=total,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        await self._save_session(session_data)
        return session_id

    async def get_session(self, session_id: str) -> Optional[CheckoutSessionData]:
        """
        Get checkout session by ID.

        Args:
            session_id: Checkout session ID

        Returns:
            CheckoutSessionData if found, None otherwise
        """
        client = await self._get_redis()
        key = self._key(session_id)

        data = await client.get(key)
        if not data:
            return None

        session_dict = json.loads(data)
        # Convert string decimals back to Decimal
        session_dict["subtotal"] = Decimal(session_dict.get("subtotal", "0"))
        session_dict["shipping_cost"] = Decimal(session_dict.get("shipping_cost", "0"))
        session_dict["discount_amount"] = Decimal(session_dict.get("discount_amount", "0"))
        session_dict["total"] = Decimal(session_dict.get("total", "0"))

        return CheckoutSessionData(**session_dict)

    async def _save_session(self, session: CheckoutSessionData) -> None:
        """Save checkout session to Redis with TTL."""
        client = await self._get_redis()
        key = self._key(session.session_id)

        # Serialize with Decimal handling
        session_data = session.model_dump()
        session_data["subtotal"] = str(session_data["subtotal"])
        session_data["shipping_cost"] = str(session_data["shipping_cost"])
        session_data["discount_amount"] = str(session_data["discount_amount"])
        session_data["total"] = str(session_data["total"])

        await client.setex(key, self._ttl, json.dumps(session_data))

    async def delete_session(self, session_id: str) -> None:
        """
        Delete checkout session.

        Args:
            session_id: Checkout session ID
        """
        client = await self._get_redis()
        key = self._key(session_id)
        await client.delete(key)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Singleton instance for dependency injection
_checkout_session_service: Optional[CheckoutSessionService] = None


def get_checkout_session_service() -> CheckoutSessionService:
    """
    Get checkout session service singleton.

    Use as FastAPI dependency:
        checkout_service: CheckoutSessionService = Depends(get_checkout_session_service)
    """
    global _checkout_session_service
    if _checkout_session_service is None:
        _checkout_session_service = CheckoutSessionService()
    return _checkout_session_service
