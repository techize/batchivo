"""ProductionRunPlate service for managing production run plates."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.production_run_plate import ProductionRunPlate
from app.models.production_run import ProductionRun
from app.models.model import Model
from app.models.printer import Printer
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.production_run_plate import (
    ProductionRunPlateCreate,
    ProductionRunPlateUpdate,
    ProductionRunPlateResponse,
    ProductionRunPlateListResponse,
    MarkPlateCompleteRequest,
)

logger = logging.getLogger(__name__)


class ProductionRunPlateService:
    """Service for managing production run plates."""

    def __init__(self, db: AsyncSession, tenant: Tenant, user: Optional[User] = None):
        """
        Initialize the production run plate service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Current tenant for isolation
            user: Current user performing actions (optional, for audit trail)
        """
        self.db = db
        self.tenant = tenant
        self.user = user

    async def create_plate(
        self,
        production_run_id: UUID,
        data: ProductionRunPlateCreate,
    ) -> ProductionRunPlate:
        """
        Create a new production run plate.

        Args:
            production_run_id: UUID of the production run
            data: ProductionRunPlateCreate schema with plate data

        Returns:
            Created ProductionRunPlate instance

        Raises:
            ValueError: If production run, model, or printer doesn't exist or doesn't belong to tenant
        """
        # Verify production run exists and belongs to tenant
        run = await self._get_production_run(production_run_id)
        if not run:
            raise ValueError(
                f"Production run {production_run_id} not found or doesn't belong to tenant"
            )

        # Verify model exists and belongs to tenant
        model_result = await self.db.execute(
            select(Model).where(Model.id == data.model_id).where(Model.tenant_id == self.tenant.id)
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Model {data.model_id} not found or doesn't belong to tenant")

        # Verify printer exists and belongs to tenant
        printer_result = await self.db.execute(
            select(Printer)
            .where(Printer.id == data.printer_id)
            .where(Printer.tenant_id == self.tenant.id)
        )
        printer = printer_result.scalar_one_or_none()
        if not printer:
            raise ValueError(f"Printer {data.printer_id} not found or doesn't belong to tenant")

        plate = ProductionRunPlate(
            production_run_id=production_run_id,
            **data.model_dump(),
        )

        self.db.add(plate)
        await self.db.commit()
        await self.db.refresh(plate)

        # Update production run plate counts
        await self._update_run_plate_counts(production_run_id)

        # Load relationships
        await self._load_relationships(plate)

        logger.info(
            f"Created plate '{plate.plate_name}' (id={plate.id}) for run {production_run_id}"
        )
        return plate

    async def get_plate(self, plate_id: UUID) -> Optional[ProductionRunPlate]:
        """
        Get a plate by ID.

        Args:
            plate_id: UUID of the plate

        Returns:
            ProductionRunPlate instance or None if not found
        """
        result = await self.db.execute(
            select(ProductionRunPlate)
            .where(ProductionRunPlate.id == plate_id)
            .options(
                selectinload(ProductionRunPlate.model),
                selectinload(ProductionRunPlate.printer),
                selectinload(ProductionRunPlate.production_run),
            )
        )
        plate = result.scalar_one_or_none()

        # Verify tenant access through production run
        if plate and plate.production_run:
            if plate.production_run.tenant_id != self.tenant.id:
                return None

        return plate

    async def list_plates_for_run(
        self,
        production_run_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> ProductionRunPlateListResponse:
        """
        List all plates for a production run.

        Args:
            production_run_id: UUID of the production run
            status: Optional filter by plate status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            ProductionRunPlateListResponse with plates and pagination info
        """
        # Verify production run belongs to tenant
        run = await self._get_production_run(production_run_id)
        if not run:
            return ProductionRunPlateListResponse(plates=[], total=0, skip=skip, limit=limit)

        # Build query
        query = (
            select(ProductionRunPlate)
            .where(ProductionRunPlate.production_run_id == production_run_id)
            .options(
                selectinload(ProductionRunPlate.model),
                selectinload(ProductionRunPlate.printer),
            )
        )

        if status:
            query = query.where(ProductionRunPlate.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results ordered by plate number
        query = query.order_by(ProductionRunPlate.plate_number).offset(skip).limit(limit)
        result = await self.db.execute(query)
        plates = list(result.scalars().all())

        return ProductionRunPlateListResponse(
            plates=[ProductionRunPlateResponse.model_validate(p) for p in plates],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def update_plate(
        self,
        plate_id: UUID,
        data: ProductionRunPlateUpdate,
    ) -> Optional[ProductionRunPlate]:
        """
        Update a production run plate.

        Args:
            plate_id: UUID of the plate to update
            data: ProductionRunPlateUpdate schema with fields to update

        Returns:
            Updated ProductionRunPlate instance or None if not found
        """
        plate = await self.get_plate(plate_id)
        if not plate:
            return None

        # Track if status changed to complete
        was_complete = plate.status == "complete"

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plate, field, value)

        await self.db.commit()
        await self.db.refresh(plate)

        # Update run plate counts if status changed
        is_complete = plate.status == "complete"
        if was_complete != is_complete:
            await self._update_run_plate_counts(plate.production_run_id)

        # Reload relationships
        await self._load_relationships(plate)

        logger.info(f"Updated plate '{plate.plate_name}' (id={plate.id}), status={plate.status}")
        return plate

    async def start_plate(self, plate_id: UUID) -> Optional[ProductionRunPlate]:
        """
        Mark a plate as started (printing).

        Args:
            plate_id: UUID of the plate to start

        Returns:
            Updated ProductionRunPlate instance or None if not found
        """
        plate = await self.get_plate(plate_id)
        if not plate:
            return None

        if plate.status != "pending":
            raise ValueError(f"Cannot start plate in '{plate.status}' status, must be 'pending'")

        plate.status = "printing"
        plate.started_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(plate)
        await self._load_relationships(plate)

        logger.info(f"Started plate '{plate.plate_name}' (id={plate.id})")
        return plate

    async def complete_plate(
        self,
        plate_id: UUID,
        data: MarkPlateCompleteRequest,
    ) -> Optional[ProductionRunPlate]:
        """
        Mark a plate as complete with results.

        Args:
            plate_id: UUID of the plate to complete
            data: MarkPlateCompleteRequest with completion data

        Returns:
            Updated ProductionRunPlate instance or None if not found
        """
        plate = await self.get_plate(plate_id)
        if not plate:
            return None

        if plate.status not in ("pending", "printing"):
            raise ValueError(f"Cannot complete plate in '{plate.status}' status")

        plate.status = "complete"
        plate.completed_at = datetime.now(timezone.utc)
        plate.successful_prints = data.successful_prints
        plate.failed_prints = data.failed_prints

        if data.actual_print_time_minutes is not None:
            plate.actual_print_time_minutes = data.actual_print_time_minutes
        if data.actual_material_weight_grams is not None:
            plate.actual_material_weight_grams = data.actual_material_weight_grams
        if data.notes:
            plate.notes = data.notes

        await self.db.commit()
        await self.db.refresh(plate)

        # Update run plate counts
        await self._update_run_plate_counts(plate.production_run_id)

        # Reload relationships
        await self._load_relationships(plate)

        logger.info(
            f"Completed plate '{plate.plate_name}' (id={plate.id}), "
            f"successful={data.successful_prints}, failed={data.failed_prints}"
        )
        return plate

    async def fail_plate(
        self,
        plate_id: UUID,
        notes: Optional[str] = None,
    ) -> Optional[ProductionRunPlate]:
        """
        Mark a plate as failed.

        Args:
            plate_id: UUID of the plate to fail
            notes: Optional failure notes

        Returns:
            Updated ProductionRunPlate instance or None if not found
        """
        plate = await self.get_plate(plate_id)
        if not plate:
            return None

        if plate.status == "complete":
            raise ValueError("Cannot fail a completed plate")

        plate.status = "failed"
        plate.completed_at = datetime.now(timezone.utc)
        if notes:
            plate.notes = notes

        await self.db.commit()
        await self.db.refresh(plate)
        await self._load_relationships(plate)

        logger.info(f"Failed plate '{plate.plate_name}' (id={plate.id})")
        return plate

    async def cancel_plate(
        self,
        plate_id: UUID,
        notes: Optional[str] = None,
    ) -> Optional[ProductionRunPlate]:
        """
        Cancel a plate.

        Args:
            plate_id: UUID of the plate to cancel
            notes: Optional cancellation notes

        Returns:
            Updated ProductionRunPlate instance or None if not found
        """
        plate = await self.get_plate(plate_id)
        if not plate:
            return None

        if plate.status == "complete":
            raise ValueError("Cannot cancel a completed plate")

        plate.status = "cancelled"
        if notes:
            plate.notes = notes

        await self.db.commit()
        await self.db.refresh(plate)

        # Update run plate counts
        await self._update_run_plate_counts(plate.production_run_id)

        await self._load_relationships(plate)

        logger.info(f"Cancelled plate '{plate.plate_name}' (id={plate.id})")
        return plate

    async def delete_plate(self, plate_id: UUID) -> bool:
        """
        Delete a production run plate.

        Args:
            plate_id: UUID of the plate to delete

        Returns:
            True if deleted, False if not found
        """
        plate = await self.get_plate(plate_id)
        if not plate:
            return False

        production_run_id = plate.production_run_id

        await self.db.delete(plate)
        await self.db.commit()

        # Update run plate counts
        await self._update_run_plate_counts(production_run_id)

        logger.info(f"Deleted plate (id={plate_id})")
        return True

    async def get_next_plate_number(self, production_run_id: UUID) -> int:
        """
        Get the next plate number for a production run.

        Args:
            production_run_id: UUID of the production run

        Returns:
            Next available plate number (max + 1)
        """
        result = await self.db.execute(
            select(func.max(ProductionRunPlate.plate_number)).where(
                ProductionRunPlate.production_run_id == production_run_id
            )
        )
        max_number = result.scalar()
        return (max_number or 0) + 1

    async def _get_production_run(self, production_run_id: UUID) -> Optional[ProductionRun]:
        """Get production run with tenant verification."""
        result = await self.db.execute(
            select(ProductionRun)
            .where(ProductionRun.id == production_run_id)
            .where(ProductionRun.tenant_id == self.tenant.id)
        )
        return result.scalar_one_or_none()

    async def _update_run_plate_counts(self, production_run_id: UUID) -> None:
        """Update the plate counts on the production run."""
        # Count total plates
        total_result = await self.db.execute(
            select(func.count()).where(ProductionRunPlate.production_run_id == production_run_id)
        )
        total_plates = total_result.scalar() or 0

        # Count completed plates
        completed_result = await self.db.execute(
            select(func.count())
            .where(ProductionRunPlate.production_run_id == production_run_id)
            .where(ProductionRunPlate.status == "complete")
        )
        completed_plates = completed_result.scalar() or 0

        # Update production run
        await self.db.execute(
            update(ProductionRun)
            .where(ProductionRun.id == production_run_id)
            .values(total_plates=total_plates, completed_plates=completed_plates)
        )
        await self.db.commit()

    async def _load_relationships(self, plate: ProductionRunPlate) -> None:
        """Load relationships for a plate."""
        result = await self.db.execute(
            select(ProductionRunPlate)
            .where(ProductionRunPlate.id == plate.id)
            .options(
                selectinload(ProductionRunPlate.model),
                selectinload(ProductionRunPlate.printer),
                selectinload(ProductionRunPlate.production_run),
            )
        )
        loaded = result.scalar_one()
        plate.model = loaded.model
        plate.printer = loaded.printer
        plate.production_run = loaded.production_run
