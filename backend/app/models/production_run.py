"""
Production Run SQLAlchemy Models

Models for tracking production runs (print jobs) including:
- ProductionRun: Main production run record
- ProductionRunItem: Items printed in a run
- ProductionRunMaterial: Materials/filament used in a run
"""

from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    Numeric,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

if TYPE_CHECKING:
    pass


class ProductionRun(Base):
    """
    Production Run model - represents a single print job (one bed load).

    Can contain multiple products (batch printing) and multiple materials (multi-color).
    Tracks estimated vs actual filament usage for variance analysis.

    For multi-plate runs (e.g., producing 5× Terrarium Sets requiring 37 plates),
    the run tracks overall progress via total_plates/completed_plates while
    individual plates are stored in ProductionRunPlate.

    Mode detection:
    - If total_plates > 0: Multi-plate run (use plates relationship)
    - If total_plates == 0: Legacy item-based run (use items relationship)
    """

    __tablename__ = "production_runs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )

    # Multi-plate run support
    printer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("printers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Primary printer used for this run",
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        comment="Product being produced (if making sellable product)",
    )

    # Plate tracking for multi-plate runs
    total_plates = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Total number of plates in this run",
    )
    completed_plates = Column(
        Integer, nullable=False, default=0, server_default="0", comment="Number of plates completed"
    )

    # Identification
    run_number = Column(String(50), nullable=False)  # Format: {tenant_short}-YYYYMMDD-NNN

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Numeric(6, 2), nullable=True)

    # Slicer estimates - split by type
    estimated_print_time_hours = Column(Numeric(6, 2), nullable=True)
    estimated_model_weight_grams = Column(
        Numeric(10, 2), nullable=True
    )  # Filament for actual models
    estimated_flushed_grams = Column(
        Numeric(10, 2), nullable=True
    )  # Purge/flush during color changes
    estimated_tower_grams = Column(Numeric(10, 2), nullable=True)  # Purge tower material
    estimated_total_weight_grams = Column(Numeric(10, 2), nullable=True)  # Auto-calculated total

    # Actual usage - split by type
    actual_model_weight_grams = Column(Numeric(10, 2), nullable=True)
    actual_flushed_grams = Column(Numeric(10, 2), nullable=True)
    actual_tower_grams = Column(Numeric(10, 2), nullable=True)
    actual_total_weight_grams = Column(Numeric(10, 2), nullable=True)

    # Waste tracking
    waste_filament_grams = Column(Numeric(10, 2), nullable=True)
    waste_reason = Column(Text, nullable=True)

    # Cost analysis (calculated on completion)
    cost_per_gram_actual = Column(
        Numeric(10, 6),
        nullable=True,
        comment="Actual cost per gram = total_material_cost / successful_weight",
    )
    successful_weight_grams = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Total theoretical weight of successful items (for cost calculation)",
    )

    # Metadata
    slicer_software = Column(String(100), nullable=True)
    printer_name = Column(String(100), nullable=True)
    bed_temperature = Column(Integer, nullable=True)
    nozzle_temperature = Column(Integer, nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="in_progress")

    # Quality & failure tracking
    quality_rating = Column(Integer, nullable=True)
    quality_notes = Column(Text, nullable=True)

    # Reprint tracking
    original_run_id = Column(
        UUID(as_uuid=True), ForeignKey("production_runs.id", ondelete="SET NULL"), nullable=True
    )
    is_reprint = Column(Boolean, nullable=False, default=False)

    # Notes
    notes = Column(Text, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="production_runs")
    items = relationship(
        "ProductionRunItem", back_populates="production_run", cascade="all, delete-orphan"
    )
    materials = relationship(
        "ProductionRunMaterial", back_populates="production_run", cascade="all, delete-orphan"
    )

    # Multi-plate run relationships
    printer = relationship("Printer", back_populates="production_runs", lazy="selectin")
    product = relationship("Product", back_populates="production_runs", lazy="selectin")
    plates = relationship(
        "ProductionRunPlate",
        back_populates="production_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Reprint relationships
    original_run = relationship("ProductionRun", remote_side=[id], foreign_keys=[original_run_id])
    reprints = relationship(
        "ProductionRun", back_populates="original_run", foreign_keys=[original_run_id]
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed', 'cancelled')", name="check_status"
        ),
        CheckConstraint("quality_rating >= 1 AND quality_rating <= 5", name="check_quality_rating"),
        UniqueConstraint("tenant_id", "run_number", name="unique_run_number_per_tenant"),
        Index("idx_production_runs_tenant", "tenant_id"),
        Index("idx_production_runs_started", "started_at"),
        Index("idx_production_runs_status", "status"),
        Index(
            "idx_production_runs_original",
            "original_run_id",
            postgresql_where=Column("original_run_id").isnot(None),
        ),
        Index("idx_production_runs_printer", "printer_id"),
        Index("idx_production_runs_product", "product_id"),
    )

    @property
    def is_multi_plate(self) -> bool:
        """Check if this is a multi-plate run (vs legacy item-based run)."""
        return self.total_plates > 0

    @property
    def plates_progress_percentage(self) -> float:
        """Calculate plate completion progress as percentage."""
        if self.total_plates == 0:
            return 0.0
        return (self.completed_plates / self.total_plates) * 100.0

    @property
    def is_all_plates_complete(self) -> bool:
        """Check if all plates are complete."""
        return self.is_multi_plate and self.completed_plates >= self.total_plates

    @property
    def items_summary(self) -> Optional[str]:
        """
        Generate a summary of items/product for display in lists.

        Returns:
            - Product name for multi-plate runs (e.g., "Terrarium Set")
            - "ModelName ×qty" for single item runs (e.g., "Axolotl Head ×9")
            - "N models" for multi-item runs (e.g., "3 models")
            - None if no items or product
        """
        # Multi-plate runs: use product name
        if self.is_multi_plate and self.product:
            return self.product.name

        # Legacy item-based runs: summarize items
        if self.items:
            if len(self.items) == 1:
                item = self.items[0]
                model_name = item.model.name if item.model else "Unknown"
                if item.quantity > 1:
                    return f"{model_name} ×{item.quantity}"
                return model_name
            # Multiple items: count unique models
            return f"{len(self.items)} models"

        return None

    def __repr__(self):
        return f"<ProductionRun(id={self.id}, run_number={self.run_number}, status={self.status})>"


class ProductionRunItem(Base):
    """
    Production Run Item model - represents models printed in a production run.

    Supports batch printing (multiple quantities of the same model) and
    multi-model beds (different models on one bed).
    """

    __tablename__ = "production_run_items"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_run_id = Column(
        UUID(as_uuid=True), ForeignKey("production_runs.id", ondelete="CASCADE"), nullable=False
    )
    model_id = Column(
        UUID(as_uuid=True), ForeignKey("models.id", ondelete="RESTRICT"), nullable=False
    )

    # Quantity tracking
    quantity = Column(Integer, nullable=False)
    successful_quantity = Column(Integer, nullable=False, default=0)
    failed_quantity = Column(Integer, nullable=False, default=0)

    # Position tracking (for multi-product beds)
    bed_position = Column(String(50), nullable=True)

    # Estimated costs (captured at time of print creation from product BOM)
    estimated_material_cost = Column(Numeric(10, 2), nullable=True)
    estimated_component_cost = Column(Numeric(10, 2), nullable=True)
    estimated_labor_cost = Column(Numeric(10, 2), nullable=True)
    estimated_total_cost = Column(Numeric(10, 2), nullable=True)

    # Actual cost analysis (calculated on run completion)
    model_weight_grams = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Cached model weight from BOM (for cost calculation)",
    )
    actual_cost_per_unit = Column(
        Numeric(10, 4),
        nullable=True,
        comment="Actual cost per unit = model_weight × cost_per_gram_actual",
    )

    # Notes
    notes = Column(Text, nullable=True)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    production_run = relationship("ProductionRun", back_populates="items")
    model = relationship("Model", back_populates="production_run_items")

    # Constraints
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        Index("idx_production_run_items_run", "production_run_id"),
        Index("idx_production_run_items_model", "model_id"),
    )

    def __repr__(self):
        return (
            f"<ProductionRunItem(id={self.id}, model_id={self.model_id}, quantity={self.quantity})>"
        )


class ProductionRunMaterial(Base):
    """
    Production Run Material model - represents filament/spool usage in a production run.

    Supports spool weighing (before/after) for accurate usage tracking and
    variance analysis comparing estimated vs actual usage.
    """

    __tablename__ = "production_run_materials"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_run_id = Column(
        UUID(as_uuid=True), ForeignKey("production_runs.id", ondelete="CASCADE"), nullable=False
    )
    spool_id = Column(
        UUID(as_uuid=True), ForeignKey("spools.id", ondelete="RESTRICT"), nullable=False
    )

    # Slicer estimates - split by type per spool
    estimated_model_weight_grams = Column(
        Numeric(10, 2), nullable=False
    )  # Model weight from this spool
    estimated_flushed_grams = Column(
        Numeric(10, 2), nullable=False, default=0
    )  # Purge/flush from this spool
    estimated_tower_grams = Column(
        Numeric(10, 2), nullable=False, default=0
    )  # Tower from this spool

    # Spool weighing (before/after print)
    spool_weight_before_grams = Column(Numeric(10, 2), nullable=True)
    spool_weight_after_grams = Column(Numeric(10, 2), nullable=True)

    # Actual usage - split by type per spool
    actual_model_weight_grams = Column(Numeric(10, 2), nullable=True)
    actual_flushed_grams = Column(Numeric(10, 2), nullable=True)
    actual_tower_grams = Column(Numeric(10, 2), nullable=True)

    # Cost tracking (captured at time of use from spool)
    cost_per_gram = Column(Numeric(10, 4), nullable=False)

    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    production_run = relationship("ProductionRun", back_populates="materials")
    spool = relationship("Spool", back_populates="production_run_materials")

    # Constraints
    __table_args__ = (
        Index("idx_production_run_materials_run", "production_run_id"),
        Index("idx_production_run_materials_spool", "spool_id"),
    )

    # Computed properties (variance calculated in application layer)
    @property
    def estimated_total_weight(self) -> Decimal:
        """Calculate total estimated weight (model + flushed + tower)."""
        return (
            (self.estimated_model_weight_grams or Decimal("0"))
            + (self.estimated_flushed_grams or Decimal("0"))
            + (self.estimated_tower_grams or Decimal("0"))
        )

    @property
    def actual_weight_from_weighing(self) -> Optional[Decimal]:
        """Calculate actual weight from spool weighing."""
        if self.spool_weight_before_grams is not None and self.spool_weight_after_grams is not None:
            return self.spool_weight_before_grams - self.spool_weight_after_grams
        return None

    @property
    def actual_total_weight(self) -> Decimal:
        """Get total actual weight (from weighing or manual split totals)."""
        # If we have weighing data, use that
        if self.actual_weight_from_weighing is not None:
            return self.actual_weight_from_weighing
        # Otherwise sum the manual entries
        return (
            (self.actual_model_weight_grams or Decimal("0"))
            + (self.actual_flushed_grams or Decimal("0"))
            + (self.actual_tower_grams or Decimal("0"))
        )

    @property
    def variance_grams(self) -> Decimal:
        """Calculate variance between actual and estimated total."""
        return self.actual_total_weight - self.estimated_total_weight

    @property
    def variance_percentage(self) -> Decimal:
        """Calculate variance as percentage of estimated."""
        if self.estimated_total_weight > 0:
            return (self.variance_grams / self.estimated_total_weight) * Decimal("100")
        return Decimal("0")

    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost of material used."""
        return self.actual_total_weight * self.cost_per_gram

    def __repr__(self):
        return f"<ProductionRunMaterial(id={self.id}, spool_id={self.spool_id}, estimated_total={self.estimated_total_weight}g)>"
