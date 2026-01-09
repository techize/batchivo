"""Pydantic schemas for Print Queue API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.print_job import JobPriority, JobStatus, PrinterStatus


# Summary schemas for nested entities
class ModelSummary(BaseModel):
    """Summary of a Model for embedding in responses."""

    id: UUID
    sku: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class ProductSummary(BaseModel):
    """Summary of a Product for embedding in responses."""

    id: UUID
    sku: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class PrinterSummary(BaseModel):
    """Summary of a Printer for embedding in responses."""

    id: UUID
    name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    current_status: PrinterStatus

    model_config = ConfigDict(from_attributes=True)


# Print Job Schemas
class PrintJobBase(BaseModel):
    """Base print job schema with common fields."""

    model_id: Optional[UUID] = Field(None, description="Model to print")
    product_id: Optional[UUID] = Field(None, description="Product to print")
    quantity: int = Field(1, ge=1, le=100, description="Number of copies to print")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority level")
    estimated_duration_hours: Optional[Decimal] = Field(
        None, ge=0, le=999, description="Estimated print duration in hours"
    )
    reference: Optional[str] = Field(
        None, max_length=100, description="External reference (order ID, production run)"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")


class PrintJobCreate(PrintJobBase):
    """Schema for creating a new print job."""

    pass


class PrintJobUpdate(BaseModel):
    """Schema for updating a print job."""

    priority: Optional[JobPriority] = None
    estimated_duration_hours: Optional[Decimal] = Field(None, ge=0, le=999)
    reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)


class PrintJobAssign(BaseModel):
    """Schema for assigning a job to a printer."""

    printer_id: UUID = Field(..., description="ID of the printer to assign")


class PrintJobStatusUpdate(BaseModel):
    """Schema for updating job status."""

    status: JobStatus = Field(..., description="New job status")
    error_message: Optional[str] = Field(
        None, max_length=1000, description="Error message (for failed status)"
    )


class PrintJobResponse(PrintJobBase):
    """Schema for print job response."""

    id: UUID
    tenant_id: UUID
    status: JobStatus
    assigned_printer_id: Optional[UUID] = None
    queue_position: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Nested summaries
    model: Optional[ModelSummary] = None
    product: Optional[ProductSummary] = None
    assigned_printer: Optional[PrinterSummary] = None

    model_config = ConfigDict(from_attributes=True)


class PrintJobListResponse(BaseModel):
    """Paginated list of print jobs."""

    items: list[PrintJobResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Queue Statistics
class PrinterQueueStats(BaseModel):
    """Statistics for a single printer's queue."""

    printer_id: UUID
    printer_name: str
    current_status: PrinterStatus
    jobs_in_queue: int
    estimated_time_to_completion_hours: Decimal = Field(
        ..., description="ETC: sum of remaining job durations"
    )
    current_job: Optional[PrintJobResponse] = None


class QueueOverview(BaseModel):
    """Overview of the entire print queue."""

    total_pending_jobs: int
    total_queued_jobs: int
    total_printing_jobs: int
    idle_printers: int
    busy_printers: int
    printer_stats: list[PrinterQueueStats]


# Auto-Assignment
class AutoAssignResult(BaseModel):
    """Result of auto-assignment operation."""

    assigned_count: int
    assignments: list[dict]  # [{job_id, printer_id, printer_name}]
    unassigned_count: int
    unassigned_reasons: list[str]


# Printer Status Update (for integration with Bambu Lab)
class PrinterStatusUpdate(BaseModel):
    """Schema for updating printer status from external source."""

    current_status: PrinterStatus = Field(..., description="New printer status")
    current_job_id: Optional[UUID] = Field(None, description="Currently printing job (if any)")


class PrinterQueueResponse(BaseModel):
    """Printer with queue information."""

    id: UUID
    name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    bed_size_x_mm: Optional[int] = None
    bed_size_y_mm: Optional[int] = None
    bed_size_z_mm: Optional[int] = None
    is_active: bool
    current_status: PrinterStatus
    current_job_id: Optional[UUID] = None
    current_job: Optional[PrintJobResponse] = None
    queue_jobs: list[PrintJobResponse] = []
    estimated_time_to_completion_hours: Decimal = Decimal("0")

    model_config = ConfigDict(from_attributes=True)
