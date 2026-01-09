"""ProductionRunPlate model for tracking individual plates in multi-plate production runs."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from decimal import Decimal
from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.printer import Printer
    from app.models.production_run import ProductionRun


class ProductionRunPlate(Base, UUIDMixin, TimestampMixin):
    """
    ProductionRunPlate represents a single print plate within a multi-plate production run.

    In multi-plate runs, a product (e.g., Terrarium Set) requires multiple plates to complete.
    Each plate tracks:
    - What model is being printed
    - Which printer to use
    - How many times to print this plate (quantity)
    - Progress tracking (status, timing, actuals)

    Example: A "5× Terrarium Sets" run might have:
    - Plate 1: Dragon Bodies (A1 Mini) - need 2 plates, 3 per plate
    - Plate 2: Dragon Tongues (A1 Mini) - need 1 plate, 6 per plate
    - Plates 3-8: Terrarium Walls 1-6 - 6 plates each × 5 sets = 30 plates
    - etc.

    Status flow: pending → printing → complete/failed/cancelled
    """

    __tablename__ = "production_run_plates"

    # Foreign Keys
    production_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("production_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Production run this plate belongs to",
    )

    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Model being printed on this plate",
    )

    printer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("printers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Printer for this plate",
    )

    # Plate Identification
    plate_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Plate number for ordering (1, 2, 3...)",
    )

    plate_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Plate name (e.g., 'Dragon Bodies (A1 Mini)')",
    )

    # Quantity Tracking
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="How many times this plate needs to be printed",
    )

    prints_per_plate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="How many items per single plate (e.g., 3 dragons per plate)",
    )

    # Estimates
    print_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Estimated print time per plate",
    )

    estimated_material_weight_grams: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Estimated material weight per plate",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
        comment="Plate status (pending, printing, complete, failed, cancelled)",
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When plate printing started",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When plate printing completed",
    )

    # Actuals
    actual_print_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Actual print time",
    )

    actual_material_weight_grams: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Actual material used",
    )

    # Print Results
    successful_prints: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of successful prints from this plate",
    )

    failed_prints: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of failed prints from this plate",
    )

    # Actual cost analysis (calculated on run completion)
    model_weight_grams: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Cached model weight from BOM (for cost calculation)",
    )
    actual_cost_per_unit: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="Actual cost per unit = model_weight × cost_per_gram_actual",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    production_run: Mapped["ProductionRun"] = relationship(
        "ProductionRun",
        back_populates="plates",
        lazy="select",
    )

    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="production_run_plates",
        lazy="selectin",
    )

    printer: Mapped["Printer"] = relationship(
        "Printer",
        back_populates="production_run_plates",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("plate_number > 0", name="check_plate_number_positive"),
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        CheckConstraint(
            "status IN ('pending', 'printing', 'complete', 'failed', 'cancelled')",
            name="check_status_valid",
        ),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="check_completed_after_started",
        ),
        {"comment": "Individual print plates within a multi-plate production run"},
    )

    @property
    def is_complete(self) -> bool:
        """Check if plate is complete."""
        return self.status == "complete"

    @property
    def is_pending(self) -> bool:
        """Check if plate is pending."""
        return self.status == "pending"

    @property
    def is_printing(self) -> bool:
        """Check if plate is currently printing."""
        return self.status == "printing"

    @property
    def total_items_expected(self) -> int:
        """Calculate total items expected from this plate (quantity × prints_per_plate)."""
        return self.quantity * self.prints_per_plate

    @property
    def total_items_completed(self) -> int:
        """Total items successfully completed."""
        return self.successful_prints

    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage (based on successful prints vs expected)."""
        expected = self.total_items_expected
        if expected == 0:
            return 0.0
        return (self.successful_prints / expected) * 100.0

    @property
    def total_estimated_time_minutes(self) -> Optional[int]:
        """Calculate total estimated time for all prints of this plate."""
        if self.print_time_minutes and self.quantity:
            return self.print_time_minutes * self.quantity
        return None

    @property
    def total_estimated_material_grams(self) -> Optional[Decimal]:
        """Calculate total estimated material for all prints of this plate."""
        if self.estimated_material_weight_grams and self.quantity:
            return self.estimated_material_weight_grams * self.quantity
        return None

    def __repr__(self) -> str:
        return f"<ProductionRunPlate(plate_number={self.plate_number}, plate_name={self.plate_name}, status={self.status})>"
