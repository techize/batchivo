"""Print Queue API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.dependencies import get_current_tenant, RequireAdmin
from app.models.print_job import JobPriority, JobStatus
from app.models.tenant import Tenant
from app.schemas.print_queue import (
    AutoAssignResult,
    PrintJobAssign,
    PrintJobCreate,
    PrintJobListResponse,
    PrintJobResponse,
    PrintJobStatusUpdate,
    PrintJobUpdate,
    QueueOverview,
)
from app.services.print_queue_service import PrintQueueService

router = APIRouter(prefix="/print-queue", tags=["Print Queue"])


def get_queue_service(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> PrintQueueService:
    """Get print queue service instance."""
    return PrintQueueService(db=db, tenant=tenant)


# ==================== Job Endpoints ====================


@router.post("", response_model=PrintJobResponse, status_code=status.HTTP_201_CREATED)
async def create_print_job(
    data: PrintJobCreate,
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobResponse:
    """
    Add a new job to the print queue.

    Creates a job with PENDING status. Use auto-assign or manual assign
    to assign to a printer.
    """
    job = await service.add_job(data)
    return PrintJobResponse.model_validate(job)


@router.get("", response_model=PrintJobListResponse)
async def list_print_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    printer_id: Optional[UUID] = Query(None, description="Filter by assigned printer"),
    priority: Optional[JobPriority] = Query(None, description="Filter by priority"),
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobListResponse:
    """
    List print jobs with optional filtering.

    Jobs are ordered by priority (highest first), then by creation date.
    """
    return await service.list_jobs(
        page=page,
        page_size=page_size,
        status=status,
        printer_id=printer_id,
        priority=priority,
    )


@router.get("/overview", response_model=QueueOverview)
async def get_queue_overview(
    service: PrintQueueService = Depends(get_queue_service),
) -> QueueOverview:
    """
    Get overview of the entire print queue.

    Returns counts of jobs by status, printer availability, and per-printer
    statistics including estimated time to completion.
    """
    return await service.get_queue_overview()


@router.get("/{job_id}", response_model=PrintJobResponse)
async def get_print_job(
    job_id: UUID,
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobResponse:
    """Get a specific print job by ID."""
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Print job {job_id} not found",
        )
    return PrintJobResponse.model_validate(job)


@router.patch("/{job_id}", response_model=PrintJobResponse)
async def update_print_job(
    job_id: UUID,
    data: PrintJobUpdate,
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobResponse:
    """
    Update a print job.

    Only priority, estimated duration, reference, and notes can be updated.
    """
    job = await service.update_job(job_id, data)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Print job {job_id} not found",
        )
    return PrintJobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_print_job(
    job_id: UUID,
    service: PrintQueueService = Depends(get_queue_service),
    _: RequireAdmin = None,
) -> None:
    """
    Delete a print job.

    Only completed, failed, or cancelled jobs can be deleted.
    """
    deleted = await service.delete_job(job_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete job {job_id} - either not found or still active",
        )


# ==================== Assignment Endpoints ====================


@router.patch("/{job_id}/assign", response_model=PrintJobResponse)
async def assign_job_to_printer(
    job_id: UUID,
    data: PrintJobAssign,
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobResponse:
    """
    Manually assign a job to a specific printer.

    Updates job status to QUEUED and assigns to the specified printer.
    """
    job = await service.assign_to_printer(job_id, data.printer_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign job {job_id} - job not found or printer unavailable",
        )
    return PrintJobResponse.model_validate(job)


@router.post("/auto-assign", response_model=AutoAssignResult)
async def auto_assign_jobs(
    service: PrintQueueService = Depends(get_queue_service),
) -> AutoAssignResult:
    """
    Automatically assign pending jobs to available printers.

    Uses priority queue algorithm:
    1. Jobs sorted by priority (urgent > high > normal > low)
    2. Within same priority, ordered by creation date (FIFO)
    3. Matches jobs to printers based on capabilities:
       - Bed size must fit model dimensions
       - Printer must support required materials
       - Printer must be idle and active
    """
    return await service.auto_assign_jobs()


# ==================== Status Endpoints ====================


@router.post("/{job_id}/cancel", response_model=PrintJobResponse)
async def cancel_print_job(
    job_id: UUID,
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobResponse:
    """
    Cancel a print job.

    Only PENDING or QUEUED jobs can be cancelled.
    """
    job = await service.cancel_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job {job_id} - not found or already printing/completed",
        )
    return PrintJobResponse.model_validate(job)


@router.post("/{job_id}/start", response_model=PrintJobResponse)
async def start_print_job(
    job_id: UUID,
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobResponse:
    """
    Mark a job as started (printing).

    Job must be in QUEUED status. Updates printer status to PRINTING.
    """
    job = await service.start_printing(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start job {job_id} - not found or not queued",
        )
    return PrintJobResponse.model_validate(job)


@router.post("/{job_id}/complete", response_model=PrintJobResponse)
async def complete_print_job(
    job_id: UUID,
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobResponse:
    """
    Mark a job as completed.

    Job must be in PRINTING status. Updates printer status to IDLE.
    """
    job = await service.complete_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete job {job_id} - not found or not printing",
        )
    return PrintJobResponse.model_validate(job)


@router.post("/{job_id}/fail", response_model=PrintJobResponse)
async def fail_print_job(
    job_id: UUID,
    data: PrintJobStatusUpdate,
    service: PrintQueueService = Depends(get_queue_service),
) -> PrintJobResponse:
    """
    Mark a job as failed.

    Job must be in QUEUED or PRINTING status. Updates printer status to ERROR.
    """
    job = await service.fail_job(job_id, data.error_message)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot fail job {job_id} - not found or invalid status",
        )
    return PrintJobResponse.model_validate(job)
