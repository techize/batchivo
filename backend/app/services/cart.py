"""
Cart service with Redis-backed persistent storage.

Replaces in-memory cart storage for production reliability and horizontal scaling.
"""

import json
from typing import Optional
from uuid import uuid4
from decimal import Decimal

import redis.asyncio as redis
from pydantic import BaseModel

from app.config import get_settings


class CartItem(BaseModel):
    """Item in shopping cart."""

    id: str
    product_id: str
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    image_url: Optional[str] = None

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class Cart(BaseModel):
    """Shopping cart."""

    session_id: str
    items: list[CartItem] = []
    subtotal: Decimal = Decimal("0")
    item_count: int = 0

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class CartService:
    """
    Redis-backed cart service for persistent cart storage.

    Key format: cart:{session_id}
    TTL: 24 hours (configurable)
    """

    DEFAULT_TTL = 86400  # 24 hours in seconds

    def __init__(self, redis_client: Optional[redis.Redis] = None, ttl: int = DEFAULT_TTL):
        """
        Initialize cart service.

        Args:
            redis_client: Optional Redis client (for testing). If not provided,
                         creates one from settings.
            ttl: Cart TTL in seconds (default 24 hours)
        """
        self._redis = redis_client
        self._ttl = ttl
        self._initialized = False

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    def _key(self, session_id: str) -> str:
        """Generate Redis key for cart."""
        return f"cart:{session_id}"

    async def get_cart(self, session_id: str) -> Cart:
        """
        Get cart from Redis.

        Creates new empty cart if not found.

        Args:
            session_id: Cart session ID

        Returns:
            Cart object
        """
        client = await self._get_redis()
        key = self._key(session_id)

        data = await client.get(key)
        if data:
            cart_dict = json.loads(data)
            # Convert string decimals back to Decimal
            cart_dict["subtotal"] = Decimal(cart_dict.get("subtotal", "0"))
            for item in cart_dict.get("items", []):
                item["unit_price"] = Decimal(item.get("unit_price", "0"))
                item["total_price"] = Decimal(item.get("total_price", "0"))
            return Cart(**cart_dict)

        # Return new empty cart
        return Cart(session_id=session_id)

    async def save_cart(self, cart: Cart) -> None:
        """
        Save cart to Redis with TTL.

        Args:
            cart: Cart to save
        """
        client = await self._get_redis()
        key = self._key(cart.session_id)

        # Serialize with Decimal handling
        cart_data = cart.model_dump()
        cart_data["subtotal"] = str(cart_data["subtotal"])
        for item in cart_data.get("items", []):
            item["unit_price"] = str(item["unit_price"])
            item["total_price"] = str(item["total_price"])

        await client.setex(key, self._ttl, json.dumps(cart_data))

    async def add_item(
        self,
        session_id: str,
        product_id: str,
        product_name: str,
        product_sku: str,
        quantity: int,
        unit_price: Decimal,
        image_url: Optional[str] = None,
    ) -> Cart:
        """
        Add item to cart.

        If item already exists, increases quantity.

        Args:
            session_id: Cart session ID
            product_id: Product UUID
            product_name: Product display name
            product_sku: Product SKU
            quantity: Quantity to add
            unit_price: Price per unit (in pence)
            image_url: Optional product image URL

        Returns:
            Updated cart
        """
        cart = await self.get_cart(session_id)

        # Check if product already in cart
        existing_item = None
        for item in cart.items:
            if item.product_id == product_id:
                existing_item = item
                break

        if existing_item:
            existing_item.quantity += quantity
            existing_item.total_price = existing_item.unit_price * existing_item.quantity
        else:
            cart_item = CartItem(
                id=str(uuid4()),
                product_id=product_id,
                product_name=product_name,
                product_sku=product_sku,
                quantity=quantity,
                unit_price=unit_price,
                total_price=unit_price * quantity,
                image_url=image_url,
            )
            cart.items.append(cart_item)

        # Update totals
        cart.subtotal = sum(item.total_price for item in cart.items)
        cart.item_count = sum(item.quantity for item in cart.items)

        await self.save_cart(cart)
        return cart

    async def remove_item(self, session_id: str, item_id: str) -> Cart:
        """
        Remove item from cart.

        Args:
            session_id: Cart session ID
            item_id: Cart item ID to remove

        Returns:
            Updated cart
        """
        cart = await self.get_cart(session_id)
        cart.items = [item for item in cart.items if item.id != item_id]

        # Update totals
        cart.subtotal = sum(item.total_price for item in cart.items)
        cart.item_count = sum(item.quantity for item in cart.items)

        await self.save_cart(cart)
        return cart

    async def update_item(self, session_id: str, item_id: str, quantity: int) -> Cart:
        """
        Update item quantity in cart.

        If quantity <= 0, removes item.

        Args:
            session_id: Cart session ID
            item_id: Cart item ID to update
            quantity: New quantity

        Returns:
            Updated cart
        """
        if quantity <= 0:
            return await self.remove_item(session_id, item_id)

        cart = await self.get_cart(session_id)

        for item in cart.items:
            if item.id == item_id:
                item.quantity = quantity
                item.total_price = item.unit_price * quantity
                break

        # Update totals
        cart.subtotal = sum(item.total_price for item in cart.items)
        cart.item_count = sum(item.quantity for item in cart.items)

        await self.save_cart(cart)
        return cart

    async def clear_cart(self, session_id: str) -> None:
        """
        Clear/delete cart.

        Args:
            session_id: Cart session ID
        """
        client = await self._get_redis()
        key = self._key(session_id)
        await client.delete(key)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Singleton instance for dependency injection
_cart_service: Optional[CartService] = None


def get_cart_service() -> CartService:
    """
    Get cart service singleton.

    Use as FastAPI dependency:
        cart_service: CartService = Depends(get_cart_service)
    """
    global _cart_service
    if _cart_service is None:
        _cart_service = CartService()
    return _cart_service
