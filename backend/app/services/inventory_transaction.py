"""Inventory Transaction service for managing inventory audit trail."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory_transaction import InventoryTransaction, TransactionType
from app.models.production_run import ProductionRun, ProductionRunMaterial
from app.models.spool import Spool
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)


class InventoryTransactionService:
    """Service for managing inventory transactions and audit trail."""

    def __init__(self, db: AsyncSession, tenant: Tenant, user: Optional[User] = None):
        """
        Initialize the inventory transaction service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Current tenant for isolation
            user: Current user performing actions (optional)
        """
        self.db = db
        self.tenant = tenant
        self.user = user

    async def create_transaction(
        self,
        spool_id: UUID,
        transaction_type: TransactionType,
        weight_before: Decimal,
        weight_change: Decimal,
        description: str,
        production_run_id: Optional[UUID] = None,
        production_run_material_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        metadata: Optional[dict] = None,
        transaction_at: Optional[datetime] = None,
        reversal_of_id: Optional[UUID] = None,
        is_reversal: bool = False,
    ) -> InventoryTransaction:
        """
        Create an inventory transaction record.

        Args:
            spool_id: ID of the spool affected
            transaction_type: Type of transaction
            weight_before: Spool weight before transaction
            weight_change: Weight change (negative for deductions)
            description: Human-readable description
            production_run_id: Optional production run reference
            production_run_material_id: Optional material reference
            notes: Optional additional notes
            metadata: Optional additional context
            transaction_at: When the transaction occurred (defaults to now)
            reversal_of_id: ID of transaction being reversed
            is_reversal: Whether this is a reversal transaction

        Returns:
            Created InventoryTransaction instance
        """
        weight_after = weight_before + weight_change

        transaction = InventoryTransaction(
            tenant_id=self.tenant.id,
            spool_id=spool_id,
            transaction_type=transaction_type,
            weight_before=weight_before,
            weight_change=weight_change,
            weight_after=weight_after,
            production_run_id=production_run_id,
            production_run_material_id=production_run_material_id,
            user_id=self.user.id if self.user else None,
            description=description,
            notes=notes,
            metadata=metadata,
            transaction_at=transaction_at or datetime.utcnow(),
            reversal_of_id=reversal_of_id,
            is_reversal=is_reversal,
        )

        self.db.add(transaction)
        await self.db.flush()

        # Record metrics
        try:
            from app.observability.metrics import record_inventory_operation

            record_inventory_operation(
                operation_type=transaction_type.value,
                tenant_id=str(self.tenant.id),
                success=True,
            )
        except Exception as metrics_error:
            logger.warning(f"Failed to record inventory metrics: {metrics_error}")

        logger.info(
            f"Created inventory transaction: {transaction_type.value} "
            f"for spool {spool_id}, change: {weight_change}g"
        )

        return transaction

    async def get_transaction(self, transaction_id: UUID) -> Optional[InventoryTransaction]:
        """
        Get a transaction by ID.

        Args:
            transaction_id: UUID of the transaction

        Returns:
            InventoryTransaction instance or None
        """
        result = await self.db.execute(
            select(InventoryTransaction)
            .where(InventoryTransaction.id == transaction_id)
            .where(InventoryTransaction.tenant_id == self.tenant.id)
            .options(selectinload(InventoryTransaction.spool))
        )
        return result.scalar_one_or_none()

    async def list_transactions(
        self,
        spool_id: Optional[UUID] = None,
        transaction_type: Optional[TransactionType] = None,
        production_run_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[InventoryTransaction], int]:
        """
        List transactions with filtering.

        Args:
            spool_id: Filter by spool
            transaction_type: Filter by type
            production_run_id: Filter by production run
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (transactions, total_count)
        """
        query = select(InventoryTransaction).where(InventoryTransaction.tenant_id == self.tenant.id)

        if spool_id:
            query = query.where(InventoryTransaction.spool_id == spool_id)

        if transaction_type:
            query = query.where(InventoryTransaction.transaction_type == transaction_type)

        if production_run_id:
            query = query.where(InventoryTransaction.production_run_id == production_run_id)

        if start_date:
            query = query.where(InventoryTransaction.transaction_at >= start_date)

        if end_date:
            query = query.where(InventoryTransaction.transaction_at <= end_date)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(InventoryTransaction.transaction_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(InventoryTransaction.spool))
        )

        result = await self.db.execute(query)
        transactions = result.scalars().all()

        return list(transactions), total

    async def get_transactions_for_run(
        self,
        production_run_id: UUID,
    ) -> List[InventoryTransaction]:
        """
        Get all transactions associated with a production run.

        Args:
            production_run_id: UUID of the production run

        Returns:
            List of InventoryTransaction instances
        """
        result = await self.db.execute(
            select(InventoryTransaction)
            .where(InventoryTransaction.tenant_id == self.tenant.id)
            .where(InventoryTransaction.production_run_id == production_run_id)
            .order_by(InventoryTransaction.transaction_at.asc())
            .options(selectinload(InventoryTransaction.spool))
        )
        return list(result.scalars().all())

    async def create_usage_transaction(
        self,
        spool: Spool,
        weight_used: Decimal,
        production_run: ProductionRun,
        production_run_material: ProductionRunMaterial,
        variance_percentage: Optional[Decimal] = None,
    ) -> InventoryTransaction:
        """
        Create a usage transaction for production run consumption.

        This also updates the spool's current_weight.

        Args:
            spool: Spool being used
            weight_used: Amount of filament used (positive value)
            production_run: Production run consuming the material
            production_run_material: Material record
            variance_percentage: Optional variance from estimate

        Returns:
            Created InventoryTransaction
        """
        weight_before = Decimal(str(spool.current_weight))
        weight_change = -weight_used  # Negative for consumption

        # Build metadata
        metadata = {
            "run_number": production_run.run_number,
            "estimated_weight": float(production_run_material.estimated_weight_grams),
            "actual_weight": float(weight_used),
        }
        if variance_percentage is not None:
            metadata["variance_percentage"] = float(variance_percentage)

        description = (
            f"Production run {production_run.run_number}: "
            f"Used {weight_used}g from spool {spool.spool_id}"
        )

        # Update spool weight atomically
        await self.db.execute(
            update(Spool)
            .where(Spool.id == spool.id)
            .values(current_weight=Spool.current_weight - weight_used)
        )

        # Create transaction record
        transaction = await self.create_transaction(
            spool_id=spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=weight_before,
            weight_change=weight_change,
            description=description,
            production_run_id=production_run.id,
            production_run_material_id=production_run_material.id,
            metadata=metadata,
        )

        return transaction

    async def create_return_transaction(
        self,
        spool: Spool,
        weight_returned: Decimal,
        production_run: ProductionRun,
        production_run_material: ProductionRunMaterial,
        original_transaction_id: UUID,
    ) -> InventoryTransaction:
        """
        Create a return transaction when reverting a production run completion.

        This also updates the spool's current_weight.

        Args:
            spool: Spool to return material to
            weight_returned: Amount of filament to return (positive value)
            production_run: Production run being reverted
            production_run_material: Material record
            original_transaction_id: ID of the usage transaction being reversed

        Returns:
            Created InventoryTransaction
        """
        weight_before = Decimal(str(spool.current_weight))
        weight_change = weight_returned  # Positive for return

        description = (
            f"Revert production run {production_run.run_number}: "
            f"Returned {weight_returned}g to spool {spool.spool_id}"
        )

        # Update spool weight atomically
        await self.db.execute(
            update(Spool)
            .where(Spool.id == spool.id)
            .values(current_weight=Spool.current_weight + weight_returned)
        )

        # Create reversal transaction
        transaction = await self.create_transaction(
            spool_id=spool.id,
            transaction_type=TransactionType.RETURN,
            weight_before=weight_before,
            weight_change=weight_change,
            description=description,
            production_run_id=production_run.id,
            production_run_material_id=production_run_material.id,
            reversal_of_id=original_transaction_id,
            is_reversal=True,
            metadata={
                "run_number": production_run.run_number,
                "reason": "Production run completion reverted",
            },
        )

        return transaction

    async def create_adjustment_transaction(
        self,
        spool: Spool,
        new_weight: Decimal,
        reason: str,
        notes: Optional[str] = None,
    ) -> InventoryTransaction:
        """
        Create an adjustment transaction for manual weight corrections.

        Args:
            spool: Spool being adjusted
            new_weight: New weight value
            reason: Reason for adjustment
            notes: Optional additional notes

        Returns:
            Created InventoryTransaction
        """
        weight_before = Decimal(str(spool.current_weight))
        weight_change = new_weight - weight_before

        description = f"Manual adjustment: {reason}"

        # Update spool weight atomically
        await self.db.execute(
            update(Spool).where(Spool.id == spool.id).values(current_weight=new_weight)
        )

        transaction = await self.create_transaction(
            spool_id=spool.id,
            transaction_type=TransactionType.ADJUSTMENT,
            weight_before=weight_before,
            weight_change=weight_change,
            description=description,
            notes=notes,
            metadata={"reason": reason, "new_weight": float(new_weight)},
        )

        return transaction

    async def validate_sufficient_inventory(
        self,
        materials: List[ProductionRunMaterial],
    ) -> tuple[bool, List[str]]:
        """
        Validate that all spools have sufficient weight for the materials.

        Args:
            materials: List of production run materials to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        for material in materials:
            actual_weight = float(material.final_actual_weight)

            # Get current spool weight
            spool_result = await self.db.execute(select(Spool).where(Spool.id == material.spool_id))
            spool = spool_result.scalar_one()

            if float(spool.current_weight) < actual_weight:
                errors.append(
                    f"Insufficient weight in spool {spool.spool_id}: "
                    f"Required {actual_weight}g, Available {spool.current_weight}g"
                )

        return len(errors) == 0, errors

    async def get_spool_transaction_summary(
        self,
        spool_id: UUID,
    ) -> dict:
        """
        Get a summary of transactions for a spool.

        Args:
            spool_id: UUID of the spool

        Returns:
            Dictionary with transaction summary
        """
        transactions, _ = await self.list_transactions(
            spool_id=spool_id,
            page=1,
            page_size=1000,  # Get all for summary
        )

        summary = {
            "spool_id": str(spool_id),
            "total_transactions": len(transactions),
            "by_type": {},
            "total_used": Decimal("0"),
            "total_returned": Decimal("0"),
            "total_adjusted": Decimal("0"),
        }

        for tx in transactions:
            type_name = tx.transaction_type.value
            if type_name not in summary["by_type"]:
                summary["by_type"][type_name] = {"count": 0, "total_weight": Decimal("0")}

            summary["by_type"][type_name]["count"] += 1
            summary["by_type"][type_name]["total_weight"] += abs(tx.weight_change)

            if tx.transaction_type == TransactionType.USAGE:
                summary["total_used"] += abs(tx.weight_change)
            elif tx.transaction_type == TransactionType.RETURN:
                summary["total_returned"] += tx.weight_change
            elif tx.transaction_type == TransactionType.ADJUSTMENT:
                summary["total_adjusted"] += tx.weight_change

        # Convert Decimals to floats for JSON serialization
        summary["total_used"] = float(summary["total_used"])
        summary["total_returned"] = float(summary["total_returned"])
        summary["total_adjusted"] = float(summary["total_adjusted"])
        for type_data in summary["by_type"].values():
            type_data["total_weight"] = float(type_data["total_weight"])

        return summary
