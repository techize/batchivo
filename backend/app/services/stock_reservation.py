"""
Stock reservation service with Redis-backed storage.

Temporarily reserves stock during checkout to prevent overselling.
Reservations automatically expire (via Redis TTL) if checkout is not completed.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.product import Product

logger = logging.getLogger(__name__)


@dataclass
class ReservationItem:
    """Single item in a reservation."""

    product_id: str
    quantity: int
    product_name: str = ""
    product_sku: str = ""


@dataclass
class ReservationResult:
    """Result of a reservation attempt."""

    success: bool
    session_id: str
    reserved_items: list[ReservationItem]
    failed_items: list[dict]  # Items that couldn't be reserved with reason
    message: str = ""


@dataclass
class StockInfo:
    """Stock information for a product."""

    product_id: str
    total_stock: int
    reserved_stock: int
    available_stock: int


class StockReservationService:
    """
    Redis-backed stock reservation service.

    Key formats:
    - reservation:{session_id} - Hash of product_id -> quantity for a checkout session
    - product_reservations:{product_id} - Hash of session_id -> quantity for a product

    TTL: 15 minutes (matches checkout session expiry)

    This dual-key approach allows:
    1. Quick lookup of all reservations for a session (for release)
    2. Quick calculation of total reserved stock for a product (for availability)

    IMPORTANT: Stock reservation uses atomic Lua scripts to prevent race conditions
    where concurrent checkouts could oversell limited stock.
    """

    DEFAULT_TTL = 900  # 15 minutes in seconds

    # Lua script for atomic check-and-reserve
    # Args: KEYS[1]=product_key, KEYS[2]=session_key
    #       ARGV[1]=session_id, ARGV[2]=product_id, ARGV[3]=quantity,
    #       ARGV[4]=max_available, ARGV[5]=reservation_data, ARGV[6]=ttl
    # Returns: 1 if reserved, 0 if insufficient stock, -1 if error
    RESERVE_SCRIPT = """
    local product_key = KEYS[1]
    local session_key = KEYS[2]
    local session_id = ARGV[1]
    local product_id = ARGV[2]
    local quantity = tonumber(ARGV[3])
    local max_available = tonumber(ARGV[4])
    local reservation_data = ARGV[5]
    local ttl = tonumber(ARGV[6])

    -- Get current total reserved for this product
    local reservations = redis.call('HGETALL', product_key)
    local total_reserved = 0
    for i = 1, #reservations, 2 do
        total_reserved = total_reserved + tonumber(reservations[i + 1])
    end

    -- Check availability
    local available = max_available - total_reserved
    if available < quantity then
        return 0  -- Insufficient stock
    end

    -- Atomically add reservations
    redis.call('HSET', product_key, session_id, quantity)
    redis.call('EXPIRE', product_key, ttl)
    redis.call('HSET', session_key, product_id, reservation_data)
    redis.call('EXPIRE', session_key, ttl)

    return 1  -- Success
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None, ttl: int = DEFAULT_TTL):
        """
        Initialize stock reservation service.

        Args:
            redis_client: Optional Redis client (for testing)
            ttl: Reservation TTL in seconds (default 15 minutes)
        """
        self._redis = redis_client
        self._ttl = ttl
        self._reserve_script = None  # Registered Lua script

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            settings = get_settings()
            self._redis = redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
        return self._redis

    async def _get_reserve_script(self, client: redis.Redis):
        """Get or register the Lua reservation script."""
        if self._reserve_script is None:
            self._reserve_script = client.register_script(self.RESERVE_SCRIPT)
        return self._reserve_script

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session reservations."""
        return f"reservation:{session_id}"

    def _product_key(self, product_id: str) -> str:
        """Generate Redis key for product reservations."""
        return f"product_reservations:{product_id}"

    async def reserve_stock(
        self,
        session_id: str,
        items: list[ReservationItem],
        db: AsyncSession,
    ) -> ReservationResult:
        """
        Reserve stock for checkout items using atomic Lua scripts.

        This method uses Redis Lua scripts to atomically check availability
        and create reservations, preventing race conditions where concurrent
        checkouts could oversell limited stock.

        If any item cannot be reserved, the entire reservation fails
        (all-or-nothing to prevent partial checkouts).

        Args:
            session_id: Checkout session ID
            items: List of items to reserve
            db: Database session for stock lookup

        Returns:
            ReservationResult with success status and details
        """
        client = await self._get_redis()
        reserve_script = await self._get_reserve_script(client)

        # First, release any existing reservation for this session
        await self.release_reservation(session_id)

        reserved_items: list[ReservationItem] = []
        failed_items: list[dict] = []
        items_to_reserve: list[tuple[ReservationItem, Product, int]] = []

        # Phase 1: Validate products and gather info from DB
        for item in items:
            try:
                product_uuid = UUID(item.product_id)
            except ValueError:
                failed_items.append(
                    {
                        "product_id": item.product_id,
                        "reason": "Invalid product ID",
                        "requested": item.quantity,
                    }
                )
                continue

            # Get current stock from database
            result = await db.execute(select(Product).where(Product.id == product_uuid))
            product = result.scalar_one_or_none()

            if not product:
                failed_items.append(
                    {
                        "product_id": item.product_id,
                        "reason": "Product not found",
                        "requested": item.quantity,
                    }
                )
                continue

            # Check if product is print-to-order (unlimited availability)
            is_print_to_order = getattr(product, "print_to_order", False)
            max_available = 999999 if is_print_to_order else (product.units_in_stock or 0)

            items_to_reserve.append((item, product, max_available))

        # If validation failed for any items, return early
        if failed_items:
            return ReservationResult(
                success=False,
                session_id=session_id,
                reserved_items=[],
                failed_items=failed_items,
                message="Some items could not be reserved due to validation errors",
            )

        # Phase 2: Atomically reserve each item using Lua script
        session_key = self._session_key(session_id)

        for item, product, max_available in items_to_reserve:
            product_key = self._product_key(item.product_id)

            reservation_data = json.dumps(
                {
                    "quantity": item.quantity,
                    "product_name": product.name,
                    "product_sku": product.sku or "",
                    "reserved_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Atomic check-and-reserve using Lua script
            result = await reserve_script(
                keys=[product_key, session_key],
                args=[
                    session_id,
                    item.product_id,
                    str(item.quantity),
                    str(max_available),
                    reservation_data,
                    str(self._ttl),
                ],
            )

            if result == 1:
                # Successfully reserved
                reserved_items.append(
                    ReservationItem(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        product_name=product.name,
                        product_sku=product.sku or "",
                    )
                )
            else:
                # Failed to reserve (insufficient stock detected atomically)
                # Need to rollback all previously reserved items in this request
                if reserved_items:
                    await self.release_reservation(session_id)

                # Get current availability for error message
                reserved_qty = await self.get_reserved_quantity(item.product_id)
                available = max(0, max_available - reserved_qty)

                failed_items.append(
                    {
                        "product_id": item.product_id,
                        "product_name": product.name,
                        "reason": "Insufficient stock",
                        "requested": item.quantity,
                        "available": available,
                    }
                )

                return ReservationResult(
                    success=False,
                    session_id=session_id,
                    reserved_items=[],
                    failed_items=failed_items,
                    message="Some items could not be reserved due to insufficient stock",
                )

        logger.info(
            f"Reserved stock for session {session_id}: {len(reserved_items)} items reserved"
        )

        return ReservationResult(
            success=True,
            session_id=session_id,
            reserved_items=reserved_items,
            failed_items=[],
            message=f"Successfully reserved {len(reserved_items)} items",
        )

    async def release_reservation(self, session_id: str) -> bool:
        """
        Release all reservations for a session.

        Called when:
        - Checkout is cancelled
        - Session expires (handled by Redis TTL, but explicit release is faster)
        - Before creating a new reservation for same session

        Args:
            session_id: Checkout session ID

        Returns:
            True if reservations were released, False if none existed
        """
        client = await self._get_redis()
        session_key = self._session_key(session_id)

        # Get current reservations for this session
        reservations = await client.hgetall(session_key)
        if not reservations:
            return False

        pipe = client.pipeline()

        # Remove from each product's reservation hash
        for product_id in reservations.keys():
            product_key = self._product_key(product_id)
            pipe.hdel(product_key, session_id)

        # Delete session reservation hash
        pipe.delete(session_key)

        await pipe.execute()

        logger.info(f"Released reservations for session {session_id}")
        return True

    async def confirm_reservation(self, session_id: str) -> bool:
        """
        Confirm reservation (order completed - convert to permanent stock deduction).

        This removes the reservation from Redis. The actual stock deduction
        happens in the order completion code (already exists in shop.py).

        Args:
            session_id: Checkout session ID

        Returns:
            True if reservation was confirmed, False if none existed
        """
        # Simply release the reservation - stock is deducted by order completion
        result = await self.release_reservation(session_id)
        if result:
            logger.info(f"Confirmed reservation for session {session_id}")
        return result

    async def get_reserved_quantity(self, product_id: str) -> int:
        """
        Get total reserved quantity for a product.

        Args:
            product_id: Product UUID string

        Returns:
            Total quantity reserved across all sessions
        """
        client = await self._get_redis()
        product_key = self._product_key(product_id)

        reservations = await client.hgetall(product_key)
        if not reservations:
            return 0

        total = sum(int(qty) for qty in reservations.values())
        return total

    async def get_available_stock(
        self,
        product_id: str,
        db: AsyncSession,
    ) -> StockInfo:
        """
        Get available stock for a product (actual stock minus reserved).

        Args:
            product_id: Product UUID string
            db: Database session

        Returns:
            StockInfo with total, reserved, and available quantities
        """
        try:
            product_uuid = UUID(product_id)
        except ValueError:
            return StockInfo(
                product_id=product_id,
                total_stock=0,
                reserved_stock=0,
                available_stock=0,
            )

        # Get actual stock from database
        result = await db.execute(select(Product).where(Product.id == product_uuid))
        product = result.scalar_one_or_none()

        total_stock = product.units_in_stock if product else 0
        reserved = await self.get_reserved_quantity(product_id)
        available = max(0, total_stock - reserved)

        return StockInfo(
            product_id=product_id,
            total_stock=total_stock,
            reserved_stock=reserved,
            available_stock=available,
        )

    async def get_session_reservations(self, session_id: str) -> list[ReservationItem]:
        """
        Get all reservations for a session.

        Args:
            session_id: Checkout session ID

        Returns:
            List of reserved items
        """
        client = await self._get_redis()
        session_key = self._session_key(session_id)

        reservations = await client.hgetall(session_key)
        if not reservations:
            return []

        items = []
        for product_id, data_str in reservations.items():
            data = json.loads(data_str)
            items.append(
                ReservationItem(
                    product_id=product_id,
                    quantity=data["quantity"],
                    product_name=data.get("product_name", ""),
                    product_sku=data.get("product_sku", ""),
                )
            )

        return items

    async def extend_reservation(self, session_id: str, additional_seconds: int = 0) -> bool:
        """
        Extend reservation TTL.

        Useful if user is still actively in checkout.

        Args:
            session_id: Checkout session ID
            additional_seconds: Additional time (0 = reset to default TTL)

        Returns:
            True if reservation was extended, False if none existed
        """
        client = await self._get_redis()
        session_key = self._session_key(session_id)

        # Check if reservation exists
        exists = await client.exists(session_key)
        if not exists:
            return False

        new_ttl = self._ttl + additional_seconds

        # Get all product IDs to extend their TTLs too
        reservations = await client.hgetall(session_key)

        pipe = client.pipeline()
        pipe.expire(session_key, new_ttl)

        for product_id in reservations.keys():
            product_key = self._product_key(product_id)
            pipe.expire(product_key, new_ttl)

        await pipe.execute()

        logger.debug(f"Extended reservation TTL for session {session_id}")
        return True

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# Singleton instance for dependency injection
_stock_reservation_service: Optional[StockReservationService] = None


def get_stock_reservation_service() -> StockReservationService:
    """
    Get stock reservation service singleton.

    Use as FastAPI dependency:
        reservation_service: StockReservationService = Depends(get_stock_reservation_service)
    """
    global _stock_reservation_service
    if _stock_reservation_service is None:
        _stock_reservation_service = StockReservationService()
    return _stock_reservation_service
