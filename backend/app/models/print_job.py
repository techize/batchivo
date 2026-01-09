"""Print Job model for managing the print queue."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.printer import Printer
    from app.models.product import Product
    from app.models.tenant import Tenant


class JobPriority(str, enum.Enum):
    """Priority levels for print jobs."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class JobStatus(str, enum.Enum):
    """Status states for print jobs."""

    PENDING = "pending"  # Job created, not yet queued
    QUEUED = "queued"  # Job in queue, waiting for printer
    PRINTING = "printing"  # Currently printing
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Print failed
    CANCELLED = "cancelled"  # Job was cancelled


class PrinterStatus(str, enum.Enum):
    """Status states for printers in the queue system."""

    IDLE = "idle"  # Ready for new jobs
    PRINTING = "printing"  # Currently printing
    PAUSED = "paused"  # Paused mid-print
    ERROR = "error"  # Error state
    OFFLINE = "offline"  # Not connected
    MAINTENANCE = "maintenance"  # Under maintenance


class PrintJob(Base, UUIDMixin, TimestampMixin):
    """
    PrintJob represents a single print job in the queue.

    Jobs are assigned to printers based on priority and printer capabilities.
    Each job tracks its lifecycle from creation to completion.

    Multi-tenant: Each job belongs to a single tenant.
    """

    __tablename__ = "print_jobs"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # What to print - can be a Model or Product
    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Model to print (if printing a model directly)",
    )

    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Product to print (if printing for a product)",
    )

    # Job details
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Number of copies to print",
    )

    priority: Mapped[JobPriority] = mapped_column(
        Enum(JobPriority, name="job_priority", native_enum=False),
        nullable=False,
        default=JobPriority.NORMAL,
        index=True,
        comment="Job priority level",
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", native_enum=False),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
        comment="Current job status",
    )

    # Printer assignment
    assigned_printer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("printers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Printer assigned to this job",
    )

    # Time estimates and tracking
    estimated_duration_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="Estimated print duration in hours",
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When printing started",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When printing completed (success or failure)",
    )

    # Queue position tracking
    queue_position: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Position in the queue (1-indexed, null if not queued)",
    )

    # Job reference (e.g., order number, production run ID)
    reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="External reference (order ID, production run ID)",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes for the job",
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if job failed",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="print_jobs",
        lazy="select",
    )

    model: Mapped[Optional["Model"]] = relationship(
        "Model",
        back_populates="print_jobs",
        lazy="selectin",
    )

    product: Mapped[Optional["Product"]] = relationship(
        "Product",
        back_populates="print_jobs",
        lazy="selectin",
    )

    assigned_printer: Mapped[Optional["Printer"]] = relationship(
        "Printer",
        back_populates="print_jobs",
        foreign_keys=[assigned_printer_id],
        lazy="selectin",
    )

    # Indexes for queue queries
    __table_args__ = (
        # Queue ordering: priority (desc), created_at (asc)
        Index(
            "ix_print_jobs_queue_order",
            "tenant_id",
            "status",
            priority.desc(),
            "created_at",
        ),
        # Jobs by printer
        Index(
            "ix_print_jobs_printer_status",
            "assigned_printer_id",
            "status",
        ),
        {"comment": "Print jobs queue for 3D printers"},
    )

    @property
    def is_active(self) -> bool:
        """Check if job is in an active state."""
        return self.status in (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.PRINTING)

    @property
    def can_be_cancelled(self) -> bool:
        """Check if job can be cancelled."""
        return self.status in (JobStatus.PENDING, JobStatus.QUEUED)

    @property
    def item_name(self) -> str:
        """Get the name of the item being printed."""
        if self.model:
            return self.model.name
        if self.product:
            return self.product.name
        return "Unknown"

    def __repr__(self) -> str:
        return f"<PrintJob(id={self.id}, status={self.status}, priority={self.priority})>"
