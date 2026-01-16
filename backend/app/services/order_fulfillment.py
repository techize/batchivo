"""Order Fulfillment service for managing inventory deduction on order fulfillment."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.product import Product
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


@dataclass
class InsufficientStockItem:
    """Details about an item with insufficient stock."""

    product_id: UUID
    product_sku: str
    product_name: str
    required: int
    available: int


@dataclass
class FulfillmentResult:
    """Result of a fulfillment operation."""

    success: bool
    message: str
    insufficient_items: list[InsufficientStockItem]


class OrderFulfillmentService:
    """Service for managing order fulfillment and inventory deduction."""

    def __init__(self, db: AsyncSession, tenant: Tenant):
        """
        Initialize the order fulfillment service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Current tenant for isolation
        """
        self.db = db
        self.tenant = tenant

    async def validate_inventory(self, order: Order) -> FulfillmentResult:
        """
        Validate that all order items have sufficient inventory.

        Args:
            order: Order to validate

        Returns:
            FulfillmentResult with validation status
        """
        insufficient_items = []

        for item in order.items:
            if not item.product_id:
                # Product was deleted, skip validation
                continue

            # Load product with current stock
            result = await self.db.execute(
                select(Product)
                .where(Product.id == item.product_id)
                .where(Product.tenant_id == self.tenant.id)
            )
            product = result.scalar_one_or_none()

            if not product:
                insufficient_items.append(
                    InsufficientStockItem(
                        product_id=item.product_id,
                        product_sku=item.product_sku,
                        product_name=item.product_name,
                        required=item.quantity,
                        available=0,
                    )
                )
                continue

            if product.units_in_stock < item.quantity:
                insufficient_items.append(
                    InsufficientStockItem(
                        product_id=item.product_id,
                        product_sku=product.sku,
                        product_name=product.name,
                        required=item.quantity,
                        available=product.units_in_stock,
                    )
                )

        if insufficient_items:
            return FulfillmentResult(
                success=False,
                message="Insufficient inventory for one or more items",
                insufficient_items=insufficient_items,
            )

        return FulfillmentResult(
            success=True,
            message="All items have sufficient inventory",
            insufficient_items=[],
        )

    async def deduct_inventory(self, order: Order) -> FulfillmentResult:
        """
        Deduct inventory for all order items.

        Uses SELECT FOR UPDATE to prevent race conditions during concurrent
        fulfillment operations.

        Args:
            order: Order to fulfill

        Returns:
            FulfillmentResult with deduction status
        """
        insufficient_items = []
        deducted_items = []

        for item in order.items:
            if not item.product_id:
                # Product was deleted, skip
                logger.warning(
                    f"Order {order.order_number}: Skipping item {item.product_name} "
                    f"(product deleted)"
                )
                continue

            # Load product with row-level lock
            result = await self.db.execute(
                select(Product)
                .where(Product.id == item.product_id)
                .where(Product.tenant_id == self.tenant.id)
                .with_for_update()
            )
            product = result.scalar_one_or_none()

            if not product:
                insufficient_items.append(
                    InsufficientStockItem(
                        product_id=item.product_id,
                        product_sku=item.product_sku,
                        product_name=item.product_name,
                        required=item.quantity,
                        available=0,
                    )
                )
                continue

            if product.units_in_stock < item.quantity:
                insufficient_items.append(
                    InsufficientStockItem(
                        product_id=item.product_id,
                        product_sku=product.sku,
                        product_name=product.name,
                        required=item.quantity,
                        available=product.units_in_stock,
                    )
                )
                continue

            # Deduct inventory
            old_stock = product.units_in_stock
            product.units_in_stock -= item.quantity
            deducted_items.append((product, item.quantity, old_stock))

            logger.info(
                f"Order {order.order_number}: Deducted {item.quantity} units of "
                f"{product.sku} (was: {old_stock}, now: {product.units_in_stock})"
            )

        if insufficient_items:
            # Rollback any deductions (the transaction won't be committed)
            return FulfillmentResult(
                success=False,
                message="Insufficient inventory for one or more items",
                insufficient_items=insufficient_items,
            )

        # Mark order as fulfilled
        order.fulfilled_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)

        # Flush to ensure all changes are ready
        await self.db.flush()

        logger.info(
            f"Order {order.order_number}: Successfully fulfilled with {len(deducted_items)} item(s)"
        )

        return FulfillmentResult(
            success=True,
            message=f"Successfully deducted inventory for {len(deducted_items)} item(s)",
            insufficient_items=[],
        )

    async def revert_inventory(self, order: Order) -> FulfillmentResult:
        """
        Revert inventory deduction for an order (e.g., when cancelling).

        Only reverts if the order was previously fulfilled (fulfilled_at is set).

        Args:
            order: Order to revert

        Returns:
            FulfillmentResult with revert status
        """
        if not order.fulfilled_at:
            return FulfillmentResult(
                success=True,
                message="Order was not fulfilled, no inventory to revert",
                insufficient_items=[],
            )

        reverted_count = 0

        for item in order.items:
            if not item.product_id:
                # Product was deleted, skip
                continue

            # Load product with row-level lock
            result = await self.db.execute(
                select(Product)
                .where(Product.id == item.product_id)
                .where(Product.tenant_id == self.tenant.id)
                .with_for_update()
            )
            product = result.scalar_one_or_none()

            if not product:
                logger.warning(
                    f"Order {order.order_number}: Could not revert {item.product_name} "
                    f"(product not found)"
                )
                continue

            # Add inventory back
            old_stock = product.units_in_stock
            product.units_in_stock += item.quantity
            reverted_count += 1

            logger.info(
                f"Order {order.order_number}: Reverted {item.quantity} units of "
                f"{product.sku} (was: {old_stock}, now: {product.units_in_stock})"
            )

        # Clear fulfilled_at
        order.fulfilled_at = None
        order.updated_at = datetime.now(timezone.utc)

        await self.db.flush()

        logger.info(f"Order {order.order_number}: Reverted inventory for {reverted_count} item(s)")

        return FulfillmentResult(
            success=True,
            message=f"Successfully reverted inventory for {reverted_count} item(s)",
            insufficient_items=[],
        )

    async def check_low_stock_alerts(self, order: Order) -> list[dict]:
        """
        Check if any products are low on stock after fulfillment.

        Args:
            order: Order that was just fulfilled

        Returns:
            List of products that are now at or below reorder threshold
        """
        low_stock_alerts = []

        for item in order.items:
            if not item.product_id:
                continue

            result = await self.db.execute(
                select(Product)
                .where(Product.id == item.product_id)
                .where(Product.tenant_id == self.tenant.id)
            )
            product = result.scalar_one_or_none()

            if not product:
                continue

            # Check if stock is low (using a threshold of 5 as default)
            # TODO: Make this configurable per product or tenant
            reorder_threshold = 5
            if product.units_in_stock <= reorder_threshold:
                low_stock_alerts.append(
                    {
                        "product_id": str(product.id),
                        "product_sku": product.sku,
                        "product_name": product.name,
                        "current_stock": product.units_in_stock,
                        "threshold": reorder_threshold,
                    }
                )
                logger.warning(
                    f"Low stock alert: {product.sku} has {product.units_in_stock} "
                    f"units (threshold: {reorder_threshold})"
                )

        return low_stock_alerts
