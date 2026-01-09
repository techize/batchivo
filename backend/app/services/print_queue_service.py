"""Print Queue Service for managing print jobs and assignments."""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.model import Model
from app.models.print_job import JobPriority, JobStatus, PrinterStatus, PrintJob
from app.models.printer import Printer
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.print_queue import (
    AutoAssignResult,
    PrinterQueueStats,
    PrintJobCreate,
    PrintJobListResponse,
    PrintJobResponse,
    PrintJobUpdate,
    QueueOverview,
)

logger = logging.getLogger(__name__)

# Priority weights for queue ordering (higher = more urgent)
PRIORITY_WEIGHTS = {
    JobPriority.URGENT: 4,
    JobPriority.HIGH: 3,
    JobPriority.NORMAL: 2,
    JobPriority.LOW: 1,
}


class PrintQueueService:
    """Service for managing the print queue."""

    def __init__(self, db: AsyncSession, tenant: Tenant, user: Optional[User] = None):
        """
        Initialize the print queue service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Current tenant for isolation
            user: Current user performing actions (optional)
        """
        self.db = db
        self.tenant = tenant
        self.user = user

    # ==================== Job CRUD ====================

    async def add_job(self, data: PrintJobCreate) -> PrintJob:
        """
        Add a new job to the print queue.

        Args:
            data: PrintJobCreate schema with job data

        Returns:
            Created PrintJob instance
        """
        job = PrintJob(
            tenant_id=self.tenant.id,
            **data.model_dump(),
            status=JobStatus.PENDING,
        )

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        logger.info(
            f"Added print job (id={job.id}, priority={job.priority}) for tenant {self.tenant.id}"
        )
        return job

    async def get_job(self, job_id: UUID) -> Optional[PrintJob]:
        """
        Get a print job by ID.

        Args:
            job_id: UUID of the job

        Returns:
            PrintJob instance or None if not found
        """
        result = await self.db.execute(
            select(PrintJob)
            .where(PrintJob.id == job_id)
            .where(PrintJob.tenant_id == self.tenant.id)
            .options(
                selectinload(PrintJob.model),
                selectinload(PrintJob.product),
                selectinload(PrintJob.assigned_printer),
            )
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        page: int = 1,
        page_size: int = 50,
        status: Optional[JobStatus] = None,
        printer_id: Optional[UUID] = None,
        priority: Optional[JobPriority] = None,
    ) -> PrintJobListResponse:
        """
        List print jobs with filtering and pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            status: Optional filter by status
            printer_id: Optional filter by assigned printer
            priority: Optional filter by priority

        Returns:
            PrintJobListResponse with jobs and pagination info
        """
        # Build query
        query = select(PrintJob).where(PrintJob.tenant_id == self.tenant.id)

        if status:
            query = query.where(PrintJob.status == status)
        if printer_id:
            query = query.where(PrintJob.assigned_printer_id == printer_id)
        if priority:
            query = query.where(PrintJob.priority == priority)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Priority queue ordering: priority DESC, created_at ASC
        query = (
            query.order_by(
                PrintJob.priority.desc(),
                PrintJob.created_at.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
            .options(
                selectinload(PrintJob.model),
                selectinload(PrintJob.product),
                selectinload(PrintJob.assigned_printer),
            )
        )

        result = await self.db.execute(query)
        jobs = list(result.scalars().all())

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return PrintJobListResponse(
            items=[PrintJobResponse.model_validate(j) for j in jobs],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def update_job(
        self,
        job_id: UUID,
        data: PrintJobUpdate,
    ) -> Optional[PrintJob]:
        """
        Update a print job.

        Args:
            job_id: UUID of the job to update
            data: PrintJobUpdate schema with fields to update

        Returns:
            Updated PrintJob instance or None if not found
        """
        job = await self.get_job(job_id)
        if not job:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Updated print job (id={job.id})")
        return job

    async def cancel_job(self, job_id: UUID) -> Optional[PrintJob]:
        """
        Cancel a print job.

        Args:
            job_id: UUID of the job to cancel

        Returns:
            Cancelled PrintJob or None if not found or cannot be cancelled
        """
        job = await self.get_job(job_id)
        if not job:
            return None

        if not job.can_be_cancelled:
            logger.warning(f"Cannot cancel job {job_id} - status is {job.status}")
            return None

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Cancelled print job (id={job.id})")
        return job

    async def delete_job(self, job_id: UUID) -> bool:
        """
        Delete a print job (only allowed for cancelled/completed jobs).

        Args:
            job_id: UUID of the job to delete

        Returns:
            True if deleted, False if not found or cannot be deleted
        """
        job = await self.get_job(job_id)
        if not job:
            return False

        if job.is_active:
            logger.warning(f"Cannot delete active job {job_id}")
            return False

        await self.db.delete(job)
        await self.db.commit()

        logger.info(f"Deleted print job (id={job_id})")
        return True

    # ==================== Job Assignment ====================

    async def assign_to_printer(
        self,
        job_id: UUID,
        printer_id: UUID,
    ) -> Optional[PrintJob]:
        """
        Manually assign a job to a printer.

        Args:
            job_id: UUID of the job to assign
            printer_id: UUID of the printer to assign to

        Returns:
            Assigned PrintJob or None if not found
        """
        job = await self.get_job(job_id)
        if not job:
            return None

        # Verify printer exists and is active
        printer = await self._get_printer(printer_id)
        if not printer or not printer.is_active:
            logger.warning(f"Printer {printer_id} not found or inactive")
            return None

        job.assigned_printer_id = printer_id
        job.status = JobStatus.QUEUED

        # Update queue position
        await self._update_queue_positions(printer_id)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Assigned job {job_id} to printer {printer.name}")
        return job

    async def auto_assign_jobs(self) -> AutoAssignResult:
        """
        Automatically assign pending jobs to available printers.

        Uses priority queue algorithm and printer capability matching.

        Returns:
            AutoAssignResult with assignment summary
        """
        # Get pending jobs ordered by priority
        pending_jobs = await self._get_pending_jobs()

        # Get idle printers
        idle_printers = await self._get_idle_printers()

        assignments = []
        unassigned_reasons = []

        for job in pending_jobs:
            if not idle_printers:
                unassigned_reasons.append(f"Job {job.id}: No idle printers available")
                continue

            # Find matching printer
            matching_printer = await self._find_matching_printer(job, idle_printers)

            if matching_printer:
                job.assigned_printer_id = matching_printer.id
                job.status = JobStatus.QUEUED

                assignments.append(
                    {
                        "job_id": str(job.id),
                        "printer_id": str(matching_printer.id),
                        "printer_name": matching_printer.name,
                    }
                )

                # Remove from available printers if now busy
                if matching_printer.current_status != PrinterStatus.IDLE:
                    idle_printers.remove(matching_printer)
            else:
                reason = f"Job {job.id}: No compatible printer found"
                if job.model_id:
                    reason += " (model requires specific capabilities)"
                unassigned_reasons.append(reason)

        await self.db.commit()

        logger.info(f"Auto-assigned {len(assignments)} jobs, {len(unassigned_reasons)} unassigned")

        return AutoAssignResult(
            assigned_count=len(assignments),
            assignments=assignments,
            unassigned_count=len(pending_jobs) - len(assignments),
            unassigned_reasons=unassigned_reasons,
        )

    # ==================== Printer Capability Matching ====================

    async def _find_matching_printer(
        self,
        job: PrintJob,
        available_printers: list[Printer],
    ) -> Optional[Printer]:
        """
        Find a printer that can handle the job based on capabilities.

        Matching criteria:
        1. Bed size >= model dimensions
        2. Material compatibility (if model has materials)
        3. Printer is active and available

        Args:
            job: PrintJob to match
            available_printers: List of available printers

        Returns:
            Matching Printer or None
        """
        if not job.model_id:
            # No specific model - return first available printer
            return available_printers[0] if available_printers else None

        # Get model with printer configs
        model = await self._get_model_with_configs(job.model_id)
        if not model:
            return available_printers[0] if available_printers else None

        # Check each printer for compatibility
        for printer in available_printers:
            if await self._is_printer_compatible(printer, model):
                return printer

        return None

    async def _is_printer_compatible(
        self,
        printer: Printer,
        model: Model,
    ) -> bool:
        """
        Check if a printer is compatible with a model.

        Args:
            printer: Printer to check
            model: Model to print

        Returns:
            True if compatible
        """
        # Check if printer has specific config for this model
        for config in model.printer_configs:
            if config.printer_id == printer.id:
                return True

        # Check bed size (if model has dimension requirements)
        # This would require model dimensions to be stored
        # For now, assume compatibility if no specific config

        # Check material compatibility from capabilities
        if printer.capabilities and model.materials:
            printer_materials = printer.capabilities.get("materials", [])
            for material in model.materials:
                if material.material_code not in printer_materials:
                    # Material not supported
                    return False

        return True

    # ==================== Queue Statistics ====================

    async def get_queue_overview(self) -> QueueOverview:
        """
        Get overview of the entire print queue.

        Returns:
            QueueOverview with statistics
        """
        # Count jobs by status
        status_counts = await self._get_job_status_counts()

        # Count printers by status
        printer_counts = await self._get_printer_status_counts()

        # Get per-printer stats
        printer_stats = await self._get_printer_queue_stats()

        return QueueOverview(
            total_pending_jobs=status_counts.get(JobStatus.PENDING, 0),
            total_queued_jobs=status_counts.get(JobStatus.QUEUED, 0),
            total_printing_jobs=status_counts.get(JobStatus.PRINTING, 0),
            idle_printers=printer_counts.get(PrinterStatus.IDLE, 0),
            busy_printers=printer_counts.get(PrinterStatus.PRINTING, 0),
            printer_stats=printer_stats,
        )

    async def calculate_printer_etc(self, printer_id: UUID) -> Decimal:
        """
        Calculate Estimated Time to Completion for a printer.

        ETC = sum of estimated_duration_hours for queued and printing jobs.

        Args:
            printer_id: UUID of the printer

        Returns:
            ETC in hours
        """
        result = await self.db.execute(
            select(func.coalesce(func.sum(PrintJob.estimated_duration_hours), 0))
            .where(PrintJob.assigned_printer_id == printer_id)
            .where(PrintJob.status.in_([JobStatus.QUEUED, JobStatus.PRINTING]))
        )
        return Decimal(str(result.scalar() or 0))

    # ==================== Job Status Transitions ====================

    async def start_printing(self, job_id: UUID) -> Optional[PrintJob]:
        """
        Mark a job as started (printing).

        Args:
            job_id: UUID of the job

        Returns:
            Updated PrintJob or None
        """
        job = await self.get_job(job_id)
        if not job or job.status != JobStatus.QUEUED:
            return None

        job.status = JobStatus.PRINTING
        job.started_at = datetime.now(timezone.utc)

        # Update printer status
        if job.assigned_printer_id:
            printer = await self._get_printer(job.assigned_printer_id)
            if printer:
                printer.current_status = PrinterStatus.PRINTING
                printer.current_job_id = job.id

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Started printing job {job_id}")
        return job

    async def complete_job(self, job_id: UUID) -> Optional[PrintJob]:
        """
        Mark a job as completed.

        Args:
            job_id: UUID of the job

        Returns:
            Updated PrintJob or None
        """
        job = await self.get_job(job_id)
        if not job or job.status != JobStatus.PRINTING:
            return None

        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)

        # Update printer status
        if job.assigned_printer_id:
            printer = await self._get_printer(job.assigned_printer_id)
            if printer:
                printer.current_status = PrinterStatus.IDLE
                printer.current_job_id = None

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Completed print job {job_id}")
        return job

    async def fail_job(
        self,
        job_id: UUID,
        error_message: Optional[str] = None,
    ) -> Optional[PrintJob]:
        """
        Mark a job as failed.

        Args:
            job_id: UUID of the job
            error_message: Optional error message

        Returns:
            Updated PrintJob or None
        """
        job = await self.get_job(job_id)
        if not job or job.status not in (JobStatus.QUEUED, JobStatus.PRINTING):
            return None

        job.status = JobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message

        # Update printer status
        if job.assigned_printer_id:
            printer = await self._get_printer(job.assigned_printer_id)
            if printer:
                printer.current_status = PrinterStatus.ERROR
                printer.current_job_id = None

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Failed print job {job_id}: {error_message}")
        return job

    # ==================== Helper Methods ====================

    async def _get_printer(self, printer_id: UUID) -> Optional[Printer]:
        """Get a printer by ID."""
        result = await self.db.execute(
            select(Printer)
            .where(Printer.id == printer_id)
            .where(Printer.tenant_id == self.tenant.id)
        )
        return result.scalar_one_or_none()

    async def _get_model_with_configs(self, model_id: UUID) -> Optional[Model]:
        """Get a model with its printer configs."""
        result = await self.db.execute(
            select(Model).where(Model.id == model_id).options(selectinload(Model.printer_configs))
        )
        return result.scalar_one_or_none()

    async def _get_pending_jobs(self) -> list[PrintJob]:
        """Get pending jobs ordered by priority."""
        result = await self.db.execute(
            select(PrintJob)
            .where(PrintJob.tenant_id == self.tenant.id)
            .where(PrintJob.status == JobStatus.PENDING)
            .order_by(PrintJob.priority.desc(), PrintJob.created_at.asc())
            .options(selectinload(PrintJob.model))
        )
        return list(result.scalars().all())

    async def _get_idle_printers(self) -> list[Printer]:
        """Get idle printers for the tenant."""
        result = await self.db.execute(
            select(Printer)
            .where(Printer.tenant_id == self.tenant.id)
            .where(Printer.is_active.is_(True))
            .where(Printer.current_status == PrinterStatus.IDLE)
            .order_by(Printer.name)
        )
        return list(result.scalars().all())

    async def _get_job_status_counts(self) -> dict[JobStatus, int]:
        """Get count of jobs by status."""
        result = await self.db.execute(
            select(PrintJob.status, func.count())
            .where(PrintJob.tenant_id == self.tenant.id)
            .group_by(PrintJob.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def _get_printer_status_counts(self) -> dict[PrinterStatus, int]:
        """Get count of printers by status."""
        result = await self.db.execute(
            select(Printer.current_status, func.count())
            .where(Printer.tenant_id == self.tenant.id)
            .where(Printer.is_active.is_(True))
            .group_by(Printer.current_status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def _get_printer_queue_stats(self) -> list[PrinterQueueStats]:
        """Get queue statistics for each printer."""
        # Get active printers
        result = await self.db.execute(
            select(Printer)
            .where(Printer.tenant_id == self.tenant.id)
            .where(Printer.is_active.is_(True))
            .options(selectinload(Printer.current_job))
        )
        printers = list(result.scalars().all())

        if not printers:
            return []

        printer_ids = [p.id for p in printers]

        # Batch query: count jobs per printer (fixes N+1)
        job_counts_result = await self.db.execute(
            select(
                PrintJob.assigned_printer_id,
                func.count().label("job_count"),
            )
            .where(PrintJob.assigned_printer_id.in_(printer_ids))
            .where(PrintJob.status.in_([JobStatus.QUEUED, JobStatus.PRINTING]))
            .group_by(PrintJob.assigned_printer_id)
        )
        job_counts = {row[0]: row[1] for row in job_counts_result.all()}

        # Batch query: sum ETC per printer (fixes N+1)
        etc_result = await self.db.execute(
            select(
                PrintJob.assigned_printer_id,
                func.coalesce(func.sum(PrintJob.estimated_duration_hours), 0).label("etc"),
            )
            .where(PrintJob.assigned_printer_id.in_(printer_ids))
            .where(PrintJob.status.in_([JobStatus.QUEUED, JobStatus.PRINTING]))
            .group_by(PrintJob.assigned_printer_id)
        )
        etc_by_printer = {row[0]: Decimal(str(row[1])) for row in etc_result.all()}

        # Build stats from batched data
        stats = []
        for printer in printers:
            current_job_response = None
            if printer.current_job:
                current_job_response = PrintJobResponse.model_validate(printer.current_job)

            stats.append(
                PrinterQueueStats(
                    printer_id=printer.id,
                    printer_name=printer.name,
                    current_status=printer.current_status,
                    jobs_in_queue=job_counts.get(printer.id, 0),
                    estimated_time_to_completion_hours=etc_by_printer.get(printer.id, Decimal("0")),
                    current_job=current_job_response,
                )
            )

        return stats

    async def _update_queue_positions(self, printer_id: UUID) -> None:
        """Update queue positions for jobs assigned to a printer."""
        result = await self.db.execute(
            select(PrintJob)
            .where(PrintJob.assigned_printer_id == printer_id)
            .where(PrintJob.status == JobStatus.QUEUED)
            .order_by(PrintJob.priority.desc(), PrintJob.created_at.asc())
        )
        jobs = list(result.scalars().all())

        for i, job in enumerate(jobs, start=1):
            job.queue_position = i
