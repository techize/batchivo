"""Production Run service for business logic operations."""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production_run import ProductionRun, ProductionRunItem, ProductionRunMaterial
from app.models.inventory_transaction import InventoryTransaction, TransactionType
from app.models.spool import Spool
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.production_run import (
    ProductionRunCreate,
    ProductionRunUpdate,
    ProductionRunItemCreate,
    ProductionRunItemUpdate,
    ProductionRunMaterialCreate,
    ProductionRunMaterialUpdate,
)

logger = logging.getLogger(__name__)

# OpenTelemetry tracer for production run operations
tracer = trace.get_tracer(__name__)


class ProductionRunService:
    """Service for managing production runs."""

    def __init__(self, db: AsyncSession, tenant: Tenant, user: Optional[User] = None):
        """
        Initialize the production run service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Current tenant for isolation
            user: Current user performing actions (optional, for audit trail)
        """
        self.db = db
        self.tenant = tenant
        self.user = user

    async def create_production_run(
        self,
        data: ProductionRunCreate,
        items: Optional[List[ProductionRunItemCreate]] = None,
        materials: Optional[List[ProductionRunMaterialCreate]] = None,
    ) -> ProductionRun:
        """
        Create a new production run with optional items and materials.

        Args:
            data: ProductionRunCreate schema with base run data
            items: Optional list of production run items
            materials: Optional list of production run materials

        Returns:
            Created ProductionRun instance with relationships loaded
        """
        # Generate run number if not provided
        if not data.run_number:
            data.run_number = await self.generate_run_number()

        # Create production run instance
        production_run = ProductionRun(
            tenant_id=self.tenant.id,
            **data.model_dump(exclude={"run_number"}),
            run_number=data.run_number,
        )

        self.db.add(production_run)
        await self.db.flush()  # Flush to get production_run.id

        # Add items if provided
        if items:
            for item_data in items:
                item = ProductionRunItem(
                    production_run_id=production_run.id,
                    **item_data.model_dump(),
                )
                self.db.add(item)

        # Add materials if provided
        if materials:
            for material_data in materials:
                # Get cost_per_gram from spool if not provided
                if material_data.cost_per_gram == Decimal("0"):
                    spool_result = await self.db.execute(
                        select(Spool).where(Spool.id == material_data.spool_id)
                    )
                    spool = spool_result.scalar_one()
                    # cost_per_gram is a property that returns Optional[float]
                    material_data.cost_per_gram = (
                        Decimal(str(spool.cost_per_gram)) if spool.cost_per_gram else Decimal("0")
                    )

                material = ProductionRunMaterial(
                    production_run_id=production_run.id,
                    **material_data.model_dump(),
                )
                self.db.add(material)

        await self.db.commit()
        await self.db.refresh(production_run)

        # Load relationships
        await self._load_relationships(production_run)

        return production_run

    async def get_production_run(self, run_id: UUID) -> Optional[ProductionRun]:
        """
        Get a production run by ID with all relationships loaded.

        Args:
            run_id: UUID of the production run

        Returns:
            ProductionRun instance or None if not found
        """
        result = await self.db.execute(
            select(ProductionRun)
            .where(ProductionRun.id == run_id)
            .where(ProductionRun.tenant_id == self.tenant.id)
            .options(
                selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
                selectinload(ProductionRun.materials)
                .selectinload(ProductionRunMaterial.spool)
                .selectinload(Spool.material_type),
            )
        )
        return result.scalar_one_or_none()

    async def get_production_run_by_number(self, run_number: str) -> Optional[ProductionRun]:
        """
        Get a production run by run number.

        Args:
            run_number: Run number (e.g., "TENANT-20251113-001")

        Returns:
            ProductionRun instance or None if not found
        """
        result = await self.db.execute(
            select(ProductionRun)
            .where(ProductionRun.run_number == run_number)
            .where(ProductionRun.tenant_id == self.tenant.id)
            .options(
                selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
                selectinload(ProductionRun.materials)
                .selectinload(ProductionRunMaterial.spool)
                .selectinload(Spool.material_type),
            )
        )
        return result.scalar_one_or_none()

    async def list_production_runs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        started_after: Optional[datetime] = None,
        started_before: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> tuple[List[ProductionRun], int]:
        """
        List production runs with pagination and filtering.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by status
            started_after: Filter runs started after this datetime
            started_before: Filter runs started before this datetime
            search: Search by run_number, printer_name, or notes

        Returns:
            Tuple of (list of ProductionRun instances, total count)
        """
        # Base query with tenant isolation
        query = select(ProductionRun).where(ProductionRun.tenant_id == self.tenant.id)

        # Apply filters
        if status:
            query = query.where(ProductionRun.status == status)

        if started_after:
            query = query.where(ProductionRun.started_at >= started_after)

        if started_before:
            query = query.where(ProductionRun.started_at <= started_before)

        if search:
            search_filter = or_(
                ProductionRun.run_number.ilike(f"%{search}%"),
                ProductionRun.printer_name.ilike(f"%{search}%"),
                ProductionRun.notes.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Apply pagination and ordering
        query = (
            query.order_by(ProductionRun.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(
                selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
                selectinload(ProductionRun.materials)
                .selectinload(ProductionRunMaterial.spool)
                .selectinload(Spool.material_type),
            )
        )

        result = await self.db.execute(query)
        runs = result.scalars().all()

        return list(runs), total

    async def update_production_run(
        self,
        run_id: UUID,
        data: ProductionRunUpdate,
    ) -> Optional[ProductionRun]:
        """
        Update a production run.

        Args:
            run_id: UUID of the production run
            data: ProductionRunUpdate schema with fields to update

        Returns:
            Updated ProductionRun instance or None if not found
        """
        # Get existing run
        production_run = await self.get_production_run(run_id)
        if not production_run:
            return None

        # Update fields (only non-None values)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(production_run, field, value)

        await self.db.commit()
        await self.db.refresh(production_run)

        # Reload relationships
        await self._load_relationships(production_run)

        return production_run

    async def delete_production_run(self, run_id: UUID) -> bool:
        """
        Delete a production run (hard delete).

        Args:
            run_id: UUID of the production run

        Returns:
            True if deleted, False if not found
        """
        production_run = await self.get_production_run(run_id)
        if not production_run:
            return False

        await self.db.delete(production_run)
        await self.db.commit()

        return True

    async def add_item_to_run(
        self,
        run_id: UUID,
        item_data: ProductionRunItemCreate,
    ) -> Optional[ProductionRunItem]:
        """
        Add an item to an existing production run.

        Args:
            run_id: UUID of the production run
            item_data: ProductionRunItemCreate schema

        Returns:
            Created ProductionRunItem or None if run not found
        """
        production_run = await self.get_production_run(run_id)
        if not production_run:
            return None

        item = ProductionRunItem(
            production_run_id=run_id,
            **item_data.model_dump(),
        )

        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def update_item(
        self,
        item_id: UUID,
        item_data: ProductionRunItemUpdate,
    ) -> Optional[ProductionRunItem]:
        """
        Update a production run item.

        Args:
            item_id: UUID of the item
            item_data: ProductionRunItemUpdate schema

        Returns:
            Updated ProductionRunItem or None if not found
        """
        result = await self.db.execute(
            select(ProductionRunItem)
            .join(ProductionRun)
            .where(ProductionRunItem.id == item_id)
            .where(ProductionRun.tenant_id == self.tenant.id)
        )
        item = result.scalar_one_or_none()
        if not item:
            return None

        # Update fields
        update_data = item_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)

        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def add_material_to_run(
        self,
        run_id: UUID,
        material_data: ProductionRunMaterialCreate,
    ) -> Optional[ProductionRunMaterial]:
        """
        Add a material to an existing production run.

        Args:
            run_id: UUID of the production run
            material_data: ProductionRunMaterialCreate schema

        Returns:
            Created ProductionRunMaterial or None if run not found
        """
        production_run = await self.get_production_run(run_id)
        if not production_run:
            return None

        # Get cost_per_gram from spool if not provided
        if material_data.cost_per_gram == Decimal("0"):
            spool_result = await self.db.execute(
                select(Spool).where(Spool.id == material_data.spool_id)
            )
            spool = spool_result.scalar_one()
            material_data.cost_per_gram = spool.cost_per_gram or Decimal("0")

        material = ProductionRunMaterial(
            production_run_id=run_id,
            **material_data.model_dump(),
        )

        self.db.add(material)
        await self.db.commit()
        await self.db.refresh(material)

        return material

    async def update_material(
        self,
        material_id: UUID,
        material_data: ProductionRunMaterialUpdate,
    ) -> Optional[ProductionRunMaterial]:
        """
        Update a production run material.

        Args:
            material_id: UUID of the material
            material_data: ProductionRunMaterialUpdate schema

        Returns:
            Updated ProductionRunMaterial or None if not found
        """
        result = await self.db.execute(
            select(ProductionRunMaterial)
            .join(ProductionRun)
            .where(ProductionRunMaterial.id == material_id)
            .where(ProductionRun.tenant_id == self.tenant.id)
        )
        material = result.scalar_one_or_none()
        if not material:
            return None

        # Update fields
        update_data = material_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(material, field, value)

        await self.db.commit()
        await self.db.refresh(material)

        return material

    async def generate_run_number(self) -> str:
        """
        Generate a unique run number for the current tenant.

        Format: {tenant_short}-YYYYMMDD-NNN
        Example: ACME-20251113-001

        Returns:
            Generated run number string
        """
        # Get tenant short code (first 4 chars of slug, uppercase)
        tenant_short = self.tenant.slug[:4].upper()

        # Get current date
        date_str = datetime.now().strftime("%Y%m%d")

        # Find the highest sequence number for today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        result = await self.db.execute(
            select(func.count(ProductionRun.id))
            .where(ProductionRun.tenant_id == self.tenant.id)
            .where(ProductionRun.started_at >= today_start)
            .where(ProductionRun.started_at < today_end)
        )
        count = result.scalar_one()

        # Increment sequence
        sequence = count + 1

        # Format: TENANT-YYYYMMDD-001
        run_number = f"{tenant_short}-{date_str}-{sequence:03d}"

        return run_number

    async def complete_production_run(
        self,
        run_id: UUID,
    ) -> Optional[ProductionRun]:
        """
        Complete a production run and deduct materials from spool inventory.

        This method:
        1. Validates sufficient spool weight for all materials
        2. Updates run status to 'completed'
        3. Deducts actual material usage from spool current_weight
        4. Creates inventory transaction records for audit trail

        Args:
            run_id: UUID of the production run

        Returns:
            Completed ProductionRun instance or None if not found

        Raises:
            ValueError: If insufficient spool weight for deduction
        """
        with tracer.start_as_current_span("complete_production_run") as span:
            span.set_attribute("production_run.id", str(run_id))
            span.set_attribute("tenant.id", str(self.tenant.id))

            # Get production run with materials loaded
            production_run = await self.get_production_run(run_id)
            if not production_run:
                span.set_attribute("production_run.found", False)
                return None

            span.set_attribute("production_run.found", True)
            span.set_attribute("production_run.run_number", production_run.run_number)
            span.set_attribute("production_run.materials_count", len(production_run.materials))

            try:
                # Validate sufficient spool weight for all materials
                for material in production_run.materials:
                    actual_weight = float(material.actual_total_weight)

                    # Get current spool weight
                    spool_result = await self.db.execute(
                        select(Spool).where(Spool.id == material.spool_id)
                    )
                    spool = spool_result.scalar_one()

                    if float(spool.current_weight) < actual_weight:
                        error_msg = (
                            f"Insufficient weight in spool {spool.spool_id}: "
                            f"Required {actual_weight}g, Available {spool.current_weight}g"
                        )
                        span.set_status(Status(StatusCode.ERROR, error_msg))
                        span.set_attribute("error.type", "insufficient_weight")
                        raise ValueError(error_msg)

                # Deduct materials from spools and create inventory transactions
                # Count materials before commit/refresh to avoid lazy loading issues
                materials_count = len(production_run.materials)
                total_material_cost = Decimal("0")

                for material in production_run.materials:
                    actual_weight = material.actual_total_weight  # Keep as Decimal

                    # Get current spool for before weight
                    spool_result = await self.db.execute(
                        select(Spool).where(Spool.id == material.spool_id)
                    )
                    spool = spool_result.scalar_one()
                    weight_before = Decimal(str(spool.current_weight))

                    # Calculate variance percentage
                    estimated = material.estimated_total_weight
                    variance_percentage = None
                    if estimated > 0:
                        variance_percentage = ((actual_weight - estimated) / estimated) * Decimal(
                            "100"
                        )

                    # Calculate material cost
                    if material.cost_per_gram:
                        total_material_cost += actual_weight * material.cost_per_gram

                    # Update spool weight atomically
                    await self.db.execute(
                        update(Spool)
                        .where(Spool.id == material.spool_id)
                        .values(current_weight=Spool.current_weight - actual_weight)
                    )

                    # Create inventory transaction record
                    transaction = InventoryTransaction(
                        tenant_id=self.tenant.id,
                        spool_id=material.spool_id,
                        transaction_type=TransactionType.USAGE,
                        weight_before=weight_before,
                        weight_change=-actual_weight,
                        weight_after=weight_before - actual_weight,
                        production_run_id=production_run.id,
                        production_run_material_id=material.id,
                        user_id=self.user.id if self.user else None,
                        description=f"Production run {production_run.run_number}: Used {actual_weight}g from spool {spool.spool_id}",
                        transaction_at=datetime.now(),
                        transaction_metadata={
                            "run_number": production_run.run_number,
                            "estimated_weight": float(estimated),
                            "actual_weight": float(actual_weight),
                            "variance_percentage": float(variance_percentage)
                            if variance_percentage
                            else None,
                        },
                    )
                    self.db.add(transaction)

                # Calculate cost analysis (distributes waste across successful items)
                await self._calculate_cost_analysis(production_run, total_material_cost)

                # Update production run status
                production_run.status = "completed"
                if not production_run.completed_at:
                    production_run.completed_at = datetime.now(timezone.utc)

                # Calculate duration if not set
                if not production_run.duration_hours and production_run.completed_at:
                    # Ensure both timestamps are timezone-aware for comparison
                    completed = production_run.completed_at
                    started = production_run.started_at
                    if started.tzinfo is None:
                        started = started.replace(tzinfo=timezone.utc)
                    if completed.tzinfo is None:
                        completed = completed.replace(tzinfo=timezone.utc)
                    duration = completed - started
                    production_run.duration_hours = Decimal(
                        str(duration.total_seconds() / 3600)
                    ).quantize(Decimal("0.01"))

                await self.db.flush()  # Flush changes before commit
                await self.db.commit()
                await self.db.refresh(production_run)

                # Record metrics
                try:
                    from app.observability.metrics import record_production_run_completed

                    duration_seconds = (
                        (production_run.completed_at - production_run.started_at).total_seconds()
                        if production_run.completed_at and production_run.started_at
                        else 0
                    )
                    record_production_run_completed(
                        tenant_id=str(self.tenant.id),
                        duration_seconds=duration_seconds,
                        material_cost=float(total_material_cost),
                    )
                except Exception as metrics_error:
                    logger.warning(f"Failed to record metrics: {metrics_error}")

                logger.info(
                    f"Completed production run {production_run.run_number} with "
                    f"{materials_count} material transactions"
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("production_run.status", "completed")
                span.set_attribute("production_run.material_cost", float(total_material_cost))

                # Reload relationships
                await self._load_relationships(production_run)

                return production_run

            except ValueError:
                # Rollback any pending changes on validation errors
                await self.db.rollback()
                raise
            except Exception as e:
                # Rollback to prevent partial inventory updates
                await self.db.rollback()
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Failed to complete production run {run_id}, rolled back: {e}")
                raise

    async def revert_completion(
        self,
        run_id: UUID,
    ) -> Optional[ProductionRun]:
        """
        Revert a completed production run back to in_progress status.

        This method:
        1. Finds original usage transactions for the run
        2. Returns materials to spool inventory
        3. Creates reversal transaction records for audit trail
        4. Updates run status back to 'in_progress'

        Args:
            run_id: UUID of the production run

        Returns:
            Reverted ProductionRun instance or None if not found

        Raises:
            ValueError: If run is not in completed status
        """
        with tracer.start_as_current_span("revert_completion") as span:
            span.set_attribute("production_run.id", str(run_id))
            span.set_attribute("tenant.id", str(self.tenant.id))

            # Get production run with materials loaded
            production_run = await self.get_production_run(run_id)
            if not production_run:
                span.set_attribute("production_run.found", False)
                return None

            span.set_attribute("production_run.found", True)
            span.set_attribute("production_run.run_number", production_run.run_number)

            try:
                if production_run.status != "completed":
                    error_msg = "Can only revert completed production runs"
                    span.set_status(Status(StatusCode.ERROR, error_msg))
                    span.set_attribute("error.type", "invalid_status")
                    raise ValueError(error_msg)

                # Get original usage transactions for this run
                original_transactions_result = await self.db.execute(
                    select(InventoryTransaction)
                    .where(InventoryTransaction.production_run_id == run_id)
                    .where(InventoryTransaction.transaction_type == TransactionType.USAGE)
                    .where(InventoryTransaction.is_reversal is False)
                )
                original_transactions = {
                    tx.production_run_material_id: tx
                    for tx in original_transactions_result.scalars().all()
                }

                # Return materials to spools and create reversal transactions
                # Count materials before commit/refresh to avoid lazy loading issues
                materials_count = len(production_run.materials)
                span.set_attribute("production_run.materials_count", materials_count)

                for material in production_run.materials:
                    actual_weight = material.actual_total_weight  # Keep as Decimal

                    # Get current spool for before weight
                    spool_result = await self.db.execute(
                        select(Spool).where(Spool.id == material.spool_id)
                    )
                    spool = spool_result.scalar_one()
                    weight_before = Decimal(str(spool.current_weight))

                    # Update spool weight atomically
                    await self.db.execute(
                        update(Spool)
                        .where(Spool.id == material.spool_id)
                        .values(current_weight=Spool.current_weight + actual_weight)
                    )

                    # Get original transaction ID for this material (if exists)
                    original_tx = original_transactions.get(material.id)
                    reversal_of_id = original_tx.id if original_tx else None

                    # Create reversal transaction record
                    transaction = InventoryTransaction(
                        tenant_id=self.tenant.id,
                        spool_id=material.spool_id,
                        transaction_type=TransactionType.RETURN,
                        weight_before=weight_before,
                        weight_change=actual_weight,
                        weight_after=weight_before + actual_weight,
                        production_run_id=production_run.id,
                        production_run_material_id=material.id,
                        user_id=self.user.id if self.user else None,
                        description=f"Revert production run {production_run.run_number}: Returned {actual_weight}g to spool {spool.spool_id}",
                        transaction_at=datetime.now(),
                        reversal_of_id=reversal_of_id,
                        is_reversal=True,
                        transaction_metadata={
                            "run_number": production_run.run_number,
                            "reason": "Production run completion reverted",
                        },
                    )
                    self.db.add(transaction)

                # Update production run status
                production_run.status = "in_progress"

                await self.db.flush()  # Flush changes before commit
                await self.db.commit()
                await self.db.refresh(production_run)

                logger.info(
                    f"Reverted production run {production_run.run_number} with "
                    f"{materials_count} material reversals"
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("production_run.status", "in_progress")

                # Reload relationships
                await self._load_relationships(production_run)

                return production_run

            except ValueError:
                # Rollback any pending changes on validation errors
                await self.db.rollback()
                raise
            except Exception as e:
                # Rollback to prevent partial inventory updates
                await self.db.rollback()
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Failed to revert production run {run_id}, rolled back: {e}")
                raise

    async def calculate_run_variance(
        self,
        run_id: UUID,
    ) -> Optional[dict]:
        """
        Calculate comprehensive variance metrics for a production run.

        Returns variance data including:
        - Material weight variance (total and per-material)
        - Time variance
        - Success rate statistics

        Args:
            run_id: UUID of the production run

        Returns:
            Dictionary with variance metrics or None if run not found
        """
        production_run = await self.get_production_run(run_id)
        if not production_run:
            return None

        # Material weight variance
        total_estimated_weight = Decimal("0")
        total_actual_weight = Decimal("0")
        material_variances = []

        for material in production_run.materials:
            estimated = material.estimated_total_weight
            actual = material.actual_total_weight

            total_estimated_weight += estimated
            total_actual_weight += actual

            material_variances.append(
                {
                    "spool_id": str(material.spool_id),
                    "estimated_grams": float(estimated),
                    "actual_grams": float(actual),
                    "variance_grams": float(material.variance_grams),
                    "variance_percentage": float(material.variance_percentage),
                }
            )

        # Overall weight variance
        weight_variance_grams = total_actual_weight - total_estimated_weight
        weight_variance_percentage = (
            (weight_variance_grams / total_estimated_weight * Decimal("100"))
            if total_estimated_weight > 0
            else Decimal("0")
        )

        # Time variance
        time_variance_hours = None
        time_variance_percentage = None
        if production_run.duration_hours and production_run.estimated_print_time_hours:
            time_variance_hours = Decimal(str(production_run.duration_hours)) - Decimal(
                str(production_run.estimated_print_time_hours)
            )
            time_variance_percentage = (
                time_variance_hours / Decimal(str(production_run.estimated_print_time_hours))
            ) * Decimal("100")

        # Success rate statistics
        total_quantity = 0
        total_successful = 0
        total_failed = 0

        for item in production_run.items:
            total_quantity += item.quantity
            total_successful += item.successful_quantity or 0
            total_failed += item.failed_quantity or 0

        success_rate = (
            (Decimal(str(total_successful)) / Decimal(str(total_quantity)) * Decimal("100"))
            if total_quantity > 0
            else Decimal("0")
        )

        return {
            "run_id": str(run_id),
            "run_number": production_run.run_number,
            "status": production_run.status,
            "weight_variance": {
                "total_estimated_grams": float(total_estimated_weight),
                "total_actual_grams": float(total_actual_weight),
                "variance_grams": float(weight_variance_grams),
                "variance_percentage": float(weight_variance_percentage),
                "materials": material_variances,
            },
            "time_variance": {
                "estimated_hours": float(production_run.estimated_print_time_hours)
                if production_run.estimated_print_time_hours
                else None,
                "actual_hours": float(production_run.duration_hours)
                if production_run.duration_hours
                else None,
                "variance_hours": float(time_variance_hours) if time_variance_hours else None,
                "variance_percentage": float(time_variance_percentage)
                if time_variance_percentage
                else None,
            },
            "success_rate": {
                "total_quantity": total_quantity,
                "successful_quantity": total_successful,
                "failed_quantity": total_failed,
                "success_rate_percentage": float(success_rate),
            },
        }

    async def calculate_aggregate_variance(
        self,
        started_after: Optional[datetime] = None,
        started_before: Optional[datetime] = None,
        status: str = "completed",
    ) -> dict:
        """
        Calculate aggregate variance metrics across multiple production runs.

        Useful for reporting and trend analysis.

        Args:
            started_after: Filter runs started after this datetime
            started_before: Filter runs started before this datetime
            status: Filter by run status (default: completed)

        Returns:
            Dictionary with aggregate variance metrics
        """
        # Get runs matching criteria
        runs, total = await self.list_production_runs(
            page=1,
            page_size=1000,  # Large page size for aggregate calculation
            status=status,
            started_after=started_after,
            started_before=started_before,
        )

        if not runs:
            return {
                "runs_analyzed": 0,
                "aggregate_weight_variance": None,
                "aggregate_time_variance": None,
                "aggregate_success_rate": None,
            }

        # Aggregate calculations
        total_estimated_weight = Decimal("0")
        total_actual_weight = Decimal("0")
        total_estimated_time = Decimal("0")
        total_actual_time = Decimal("0")
        total_quantity = 0
        total_successful = 0
        total_failed = 0
        runs_with_time_data = 0

        for run in runs:
            # Weight aggregates
            for material in run.materials:
                total_estimated_weight += material.estimated_total_weight
                total_actual_weight += material.actual_total_weight

            # Time aggregates
            if run.duration_hours and run.estimated_print_time_hours:
                total_estimated_time += Decimal(str(run.estimated_print_time_hours))
                total_actual_time += Decimal(str(run.duration_hours))
                runs_with_time_data += 1

            # Success rate aggregates
            for item in run.items:
                total_quantity += item.quantity
                total_successful += item.successful_quantity or 0
                total_failed += item.failed_quantity or 0

        # Calculate aggregate variances
        weight_variance_grams = total_actual_weight - total_estimated_weight
        weight_variance_percentage = (
            (weight_variance_grams / total_estimated_weight * Decimal("100"))
            if total_estimated_weight > 0
            else Decimal("0")
        )

        time_variance_hours = (
            total_actual_time - total_estimated_time if runs_with_time_data > 0 else None
        )
        time_variance_percentage = (
            (time_variance_hours / total_estimated_time * Decimal("100"))
            if runs_with_time_data > 0 and total_estimated_time > 0
            else None
        )

        success_rate = (
            (Decimal(str(total_successful)) / Decimal(str(total_quantity)) * Decimal("100"))
            if total_quantity > 0
            else Decimal("0")
        )

        return {
            "runs_analyzed": len(runs),
            "aggregate_weight_variance": {
                "total_estimated_grams": float(total_estimated_weight),
                "total_actual_grams": float(total_actual_weight),
                "variance_grams": float(weight_variance_grams),
                "variance_percentage": float(weight_variance_percentage),
            },
            "aggregate_time_variance": {
                "total_estimated_hours": float(total_estimated_time)
                if runs_with_time_data > 0
                else None,
                "total_actual_hours": float(total_actual_time) if runs_with_time_data > 0 else None,
                "variance_hours": float(time_variance_hours) if time_variance_hours else None,
                "variance_percentage": float(time_variance_percentage)
                if time_variance_percentage
                else None,
                "runs_with_data": runs_with_time_data,
            },
            "aggregate_success_rate": {
                "total_quantity": total_quantity,
                "successful_quantity": total_successful,
                "failed_quantity": total_failed,
                "success_rate_percentage": float(success_rate),
            },
        }

    async def cancel_production_run(
        self,
        run_id: UUID,
        cancel_mode: str = "full_reversal",
        partial_usage: Optional[dict[UUID, Decimal]] = None,
    ) -> Optional[ProductionRun]:
        """
        Cancel a production run with options for handling materials.

        Cancel modes:
        - "full_reversal": Restore all spool weights to original (as if run never happened)
        - "record_partial": Record actual filament used up to cancellation point

        Args:
            run_id: UUID of the production run
            cancel_mode: Either "full_reversal" or "record_partial"
            partial_usage: Dict mapping spool_id to actual grams used (for record_partial mode)

        Returns:
            Cancelled ProductionRun instance or None if not found

        Raises:
            ValueError: If run is not in in_progress status or invalid cancel_mode
        """
        with tracer.start_as_current_span("cancel_production_run") as span:
            span.set_attribute("production_run.id", str(run_id))
            span.set_attribute("tenant.id", str(self.tenant.id))
            span.set_attribute("cancel_mode", cancel_mode)

            # Get production run with materials loaded
            production_run = await self.get_production_run(run_id)
            if not production_run:
                span.set_attribute("production_run.found", False)
                return None

            span.set_attribute("production_run.found", True)
            span.set_attribute("production_run.run_number", production_run.run_number)

            try:
                if production_run.status != "in_progress":
                    error_msg = "Can only cancel in-progress production runs"
                    span.set_status(Status(StatusCode.ERROR, error_msg))
                    span.set_attribute("error.type", "invalid_status")
                    raise ValueError(error_msg)

                if cancel_mode not in ("full_reversal", "record_partial"):
                    error_msg = f"Invalid cancel_mode: {cancel_mode}"
                    span.set_status(Status(StatusCode.ERROR, error_msg))
                    span.set_attribute("error.type", "invalid_cancel_mode")
                    raise ValueError(error_msg)

                if cancel_mode == "record_partial":
                    # Record the partial usage and deduct from spools
                    if not partial_usage:
                        partial_usage = {}

                    for material in production_run.materials:
                        # Use provided partial usage or fall back to 0
                        actual_used = partial_usage.get(material.spool_id, Decimal("0"))

                        if actual_used > 0:
                            # Get current spool
                            spool_result = await self.db.execute(
                                select(Spool).where(Spool.id == material.spool_id)
                            )
                            spool = spool_result.scalar_one()
                            weight_before = Decimal(str(spool.current_weight))

                            # Validate sufficient weight
                            if weight_before < actual_used:
                                error_msg = (
                                    f"Insufficient weight in spool {spool.spool_id}: "
                                    f"Requested {actual_used}g, Available {weight_before}g"
                                )
                                span.set_status(Status(StatusCode.ERROR, error_msg))
                                span.set_attribute("error.type", "insufficient_weight")
                                raise ValueError(error_msg)

                            # Update spool weight
                            await self.db.execute(
                                update(Spool)
                                .where(Spool.id == material.spool_id)
                                .values(current_weight=Spool.current_weight - actual_used)
                            )

                            # Create usage transaction
                            transaction = InventoryTransaction(
                                tenant_id=self.tenant.id,
                                spool_id=material.spool_id,
                                transaction_type=TransactionType.USAGE,
                                weight_before=weight_before,
                                weight_change=-actual_used,
                                weight_after=weight_before - actual_used,
                                production_run_id=production_run.id,
                                production_run_material_id=material.id,
                                user_id=self.user.id if self.user else None,
                                description=f"Cancelled run {production_run.run_number}: Partial usage {actual_used}g from spool {spool.spool_id}",
                                transaction_at=datetime.now(),
                                transaction_metadata={
                                    "run_number": production_run.run_number,
                                    "cancel_mode": "record_partial",
                                    "actual_used": float(actual_used),
                                },
                            )
                            self.db.add(transaction)

                # Update production run status to cancelled
                production_run.status = "cancelled"
                production_run.completed_at = datetime.now(timezone.utc)

                # Calculate duration
                duration = production_run.completed_at - production_run.started_at
                production_run.duration_hours = Decimal(
                    str(duration.total_seconds() / 3600)
                ).quantize(Decimal("0.01"))

                await self.db.flush()
                await self.db.commit()
                await self.db.refresh(production_run)

                logger.info(
                    f"Cancelled production run {production_run.run_number} with mode: {cancel_mode}"
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("production_run.status", "cancelled")

                await self._load_relationships(production_run)
                return production_run

            except ValueError:
                # Rollback any pending changes on validation errors
                await self.db.rollback()
                raise
            except Exception as e:
                # Rollback to prevent partial state changes
                await self.db.rollback()
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Failed to cancel production run {run_id}, rolled back: {e}")
                raise

    async def fail_production_run(
        self,
        run_id: UUID,
        waste_grams: dict[UUID, Decimal],
        failure_reason: str,
        notes: Optional[str] = None,
    ) -> Optional[ProductionRun]:
        """
        Mark a production run as failed and record waste materials.

        This method:
        1. Records waste materials as WASTE transaction type
        2. Deducts waste from spool inventory
        3. Updates run status to 'failed' with failure reason

        Args:
            run_id: UUID of the production run
            waste_grams: Dict mapping spool_id to grams of wasted filament
            failure_reason: Reason for failure (e.g., "spaghetti", "layer_shift", "clog")
            notes: Optional additional notes about the failure

        Returns:
            Failed ProductionRun instance or None if not found

        Raises:
            ValueError: If run is not in in_progress status
        """
        with tracer.start_as_current_span("fail_production_run") as span:
            span.set_attribute("production_run.id", str(run_id))
            span.set_attribute("tenant.id", str(self.tenant.id))
            span.set_attribute("failure_reason", failure_reason)

            # Get production run with materials loaded
            production_run = await self.get_production_run(run_id)
            if not production_run:
                span.set_attribute("production_run.found", False)
                return None

            span.set_attribute("production_run.found", True)
            span.set_attribute("production_run.run_number", production_run.run_number)

            try:
                if production_run.status != "in_progress":
                    error_msg = "Can only fail in-progress production runs"
                    span.set_status(Status(StatusCode.ERROR, error_msg))
                    span.set_attribute("error.type", "invalid_status")
                    raise ValueError(error_msg)

                total_waste = Decimal("0")

                # Process waste for each material
                for material in production_run.materials:
                    waste_amount = waste_grams.get(material.spool_id, Decimal("0"))

                    if waste_amount > 0:
                        total_waste += waste_amount

                        # Get current spool
                        spool_result = await self.db.execute(
                            select(Spool).where(Spool.id == material.spool_id)
                        )
                        spool = spool_result.scalar_one()
                        weight_before = Decimal(str(spool.current_weight))

                        # Validate sufficient weight
                        if weight_before < waste_amount:
                            error_msg = (
                                f"Insufficient weight in spool {spool.spool_id}: "
                                f"Waste amount {waste_amount}g exceeds available {weight_before}g"
                            )
                            span.set_status(Status(StatusCode.ERROR, error_msg))
                            span.set_attribute("error.type", "insufficient_weight")
                            raise ValueError(error_msg)

                        # Update spool weight
                        await self.db.execute(
                            update(Spool)
                            .where(Spool.id == material.spool_id)
                            .values(current_weight=Spool.current_weight - waste_amount)
                        )

                        # Create WASTE transaction
                        transaction = InventoryTransaction(
                            tenant_id=self.tenant.id,
                            spool_id=material.spool_id,
                            transaction_type=TransactionType.WASTE,
                            weight_before=weight_before,
                            weight_change=-waste_amount,
                            weight_after=weight_before - waste_amount,
                            production_run_id=production_run.id,
                            production_run_material_id=material.id,
                            user_id=self.user.id if self.user else None,
                            description=f"Failed run {production_run.run_number}: {failure_reason} - Waste {waste_amount}g from spool {spool.spool_id}",
                            transaction_at=datetime.now(),
                            transaction_metadata={
                                "run_number": production_run.run_number,
                                "failure_reason": failure_reason,
                                "waste_grams": float(waste_amount),
                                "notes": notes,
                            },
                        )
                        self.db.add(transaction)

                # Update production run
                production_run.status = "failed"
                production_run.completed_at = datetime.now(timezone.utc)
                production_run.waste_filament_grams = total_waste
                production_run.waste_reason = failure_reason
                if notes:
                    production_run.notes = (
                        production_run.notes or ""
                    ) + f"\n\nFailure notes: {notes}"

                # Calculate duration
                duration = production_run.completed_at - production_run.started_at
                production_run.duration_hours = Decimal(
                    str(duration.total_seconds() / 3600)
                ).quantize(Decimal("0.01"))

                await self.db.flush()
                await self.db.commit()
                await self.db.refresh(production_run)

                logger.info(
                    f"Failed production run {production_run.run_number}: {failure_reason} "
                    f"with {total_waste}g total waste"
                )

                span.set_status(Status(StatusCode.OK))
                span.set_attribute("production_run.status", "failed")
                span.set_attribute("production_run.total_waste_grams", float(total_waste))

                await self._load_relationships(production_run)
                return production_run

            except ValueError:
                # Rollback any pending changes on validation errors
                await self.db.rollback()
                raise
            except Exception as e:
                # Rollback to prevent partial inventory updates (waste transactions)
                await self.db.rollback()
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error(f"Failed to fail production run {run_id}, rolled back: {e}")
                raise

    async def _calculate_cost_analysis(
        self,
        production_run: ProductionRun,
        total_material_cost: Decimal,
    ) -> None:
        """
        Calculate cost analysis for a completed production run.

        Calculates:
        - cost_per_gram_actual = total_material_cost / total_successful_weight
        - Per-item actual_cost_per_unit = model_weight × cost_per_gram_actual

        This distributes waste (purge, tower, supports, failures) proportionally
        by weight across all successful items.

        Args:
            production_run: ProductionRun instance to calculate costs for
            total_material_cost: Total material cost from all materials
        """
        successful_weight = Decimal("0")

        # Handle multi-plate runs
        if production_run.is_multi_plate and production_run.plates:
            for plate in production_run.plates:
                if plate.successful_prints > 0 and plate.model:
                    # Get model weight from BOM
                    model_weight = await self._get_model_weight(plate.model_id)
                    plate.model_weight_grams = model_weight
                    successful_weight += Decimal(str(plate.successful_prints)) * model_weight

        # Handle legacy item-based runs
        elif production_run.items:
            for item in production_run.items:
                if item.successful_quantity > 0:
                    # Get model weight from BOM
                    model_weight = await self._get_model_weight(item.model_id)
                    item.model_weight_grams = model_weight
                    successful_weight += Decimal(str(item.successful_quantity)) * model_weight

        # Calculate cost per gram if we have successful weight
        if successful_weight > 0:
            cost_per_gram = total_material_cost / successful_weight
            production_run.cost_per_gram_actual = cost_per_gram
            production_run.successful_weight_grams = successful_weight

            # Calculate per-item/plate costs
            if production_run.is_multi_plate and production_run.plates:
                for plate in production_run.plates:
                    if plate.model_weight_grams:
                        plate.actual_cost_per_unit = plate.model_weight_grams * cost_per_gram
            elif production_run.items:
                for item in production_run.items:
                    if item.model_weight_grams:
                        item.actual_cost_per_unit = item.model_weight_grams * cost_per_gram

            logger.info(
                f"Calculated cost analysis for run {production_run.run_number}: "
                f"cost_per_gram={cost_per_gram:.6f}, successful_weight={successful_weight}g"
            )
        else:
            logger.warning(
                f"No successful items for run {production_run.run_number}, skipping cost analysis"
            )

    async def _get_model_weight(self, model_id: UUID) -> Decimal:
        """
        Get total material weight for a model from its BOM.

        Args:
            model_id: UUID of the model

        Returns:
            Total weight in grams from all BOM materials
        """
        from app.models.model_material import ModelMaterial

        result = await self.db.execute(
            select(func.sum(ModelMaterial.weight_grams)).where(ModelMaterial.model_id == model_id)
        )
        total_weight = result.scalar()
        return Decimal(str(total_weight)) if total_weight else Decimal("0")

    async def _load_relationships(self, production_run: ProductionRun) -> None:
        """
        Load all relationships for a production run.

        Args:
            production_run: ProductionRun instance to load relationships for
        """
        # Refresh with relationships
        result = await self.db.execute(
            select(ProductionRun)
            .where(ProductionRun.id == production_run.id)
            .options(
                selectinload(ProductionRun.items).selectinload(ProductionRunItem.model),
                selectinload(ProductionRun.materials)
                .selectinload(ProductionRunMaterial.spool)
                .selectinload(Spool.material_type),
            )
        )
        loaded_run = result.scalar_one()

        # Copy loaded relationships back to original instance
        production_run.items = loaded_run.items
        production_run.materials = loaded_run.materials
