"""Pydantic schemas for Production Run API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, computed_field

if TYPE_CHECKING:
    from app.schemas.printer import PrinterSummary
    from app.schemas.production_run_plate import (
        ProductionRunPlateCreate,
        ProductionRunPlateResponse,
    )


# Nested schemas for related entities (displayed in responses)
class ModelSummary(BaseModel):
    """Summary of a Model for embedding in responses."""

    id: UUID
    sku: str
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProductSummary(BaseModel):
    """Summary of a Product for embedding in responses."""

    id: UUID
    sku: str
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MaterialTypeSummary(BaseModel):
    """Summary of a MaterialType for embedding in responses."""

    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class SpoolSummary(BaseModel):
    """Summary of a Spool for embedding in responses."""

    id: UUID
    spool_id: str = Field(..., description="User-friendly spool ID (e.g., FIL-001)")
    brand: str
    color: str
    color_hex: Optional[str] = None
    finish: Optional[str] = None
    material_type: Optional[MaterialTypeSummary] = None

    model_config = ConfigDict(from_attributes=True)


# Production Run Base Schemas
class ProductionRunBase(BaseModel):
    """Base production run schema with common fields."""

    run_number: str = Field(
        ..., min_length=1, max_length=50, description="Run number (format: {tenant}-YYYYMMDD-NNN)"
    )
    started_at: datetime = Field(..., description="Start datetime of production run")
    completed_at: Optional[datetime] = Field(None, description="Completion datetime")
    duration_hours: Optional[Decimal] = Field(None, ge=0, description="Duration in hours")

    # Slicer estimates - split by type
    estimated_print_time_hours: Optional[Decimal] = Field(
        None, ge=0, description="Estimated print time from slicer"
    )
    estimated_model_weight_grams: Optional[Decimal] = Field(
        None, ge=0, description="Estimated filament for actual models"
    )
    estimated_flushed_grams: Optional[Decimal] = Field(
        None, ge=0, description="Estimated purge/flush during color changes"
    )
    estimated_tower_grams: Optional[Decimal] = Field(
        None, ge=0, description="Estimated purge tower material"
    )
    estimated_total_weight_grams: Optional[Decimal] = Field(
        None, ge=0, description="Total estimated weight (auto-calculated)"
    )

    # Actual usage - split by type
    actual_model_weight_grams: Optional[Decimal] = Field(
        None, ge=0, description="Actual filament for models"
    )
    actual_flushed_grams: Optional[Decimal] = Field(
        None, ge=0, description="Actual purge/flush used"
    )
    actual_tower_grams: Optional[Decimal] = Field(
        None, ge=0, description="Actual purge tower material"
    )
    actual_total_weight_grams: Optional[Decimal] = Field(
        None, ge=0, description="Total actual weight"
    )

    # Waste tracking
    waste_filament_grams: Optional[Decimal] = Field(
        None, ge=0, description="Wasted filament (failed prints)"
    )
    waste_reason: Optional[str] = Field(None, description="Reason for waste")

    # Metadata
    slicer_software: Optional[str] = Field(None, max_length=100, description="Slicer software used")
    printer_name: Optional[str] = Field(None, max_length=100, description="Printer name")
    bed_temperature: Optional[int] = Field(
        None, ge=0, le=200, description="Bed temperature in Celsius"
    )
    nozzle_temperature: Optional[int] = Field(
        None, ge=0, le=500, description="Nozzle temperature in Celsius"
    )

    # Status
    status: Literal["in_progress", "completed", "failed", "cancelled"] = Field(
        ..., description="Production run status"
    )

    # Quality & failure tracking
    quality_rating: Optional[int] = Field(
        None, ge=1, le=5, description="Quality rating (1-5 stars)"
    )
    quality_notes: Optional[str] = Field(None, description="Quality notes and observations")

    # Reprint tracking
    original_run_id: Optional[UUID] = Field(
        None, description="ID of original run if this is a reprint"
    )
    is_reprint: bool = Field(False, description="Whether this is a reprint of a failed run")

    # Notes
    notes: Optional[str] = Field(None, description="General notes")

    @field_validator("quality_rating")
    @classmethod
    def validate_quality_rating(cls, v: Optional[int]) -> Optional[int]:
        """Validate quality rating is between 1 and 5."""
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Quality rating must be between 1 and 5")
        return v


class ProductionRunCreate(ProductionRunBase):
    """Schema for creating a new production run."""

    # Override to make run_number optional for creation (will be auto-generated)
    run_number: Optional[str] = Field(
        None, min_length=1, max_length=50, description="Run number (auto-generated if not provided)"
    )

    # Override to make started_at optional (defaults to now if not provided)
    started_at: Optional[datetime] = Field(
        None, description="Start datetime of production run (defaults to now)"
    )

    # Default status to in_progress for new runs
    status: Literal["in_progress", "completed", "failed", "cancelled"] = Field(
        "in_progress", description="Production run status (default: in_progress)"
    )

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure completed_at is after started_at if provided."""
        if v and "started_at" in info.data:
            started_at = info.data["started_at"]
            if v < started_at:
                raise ValueError("completed_at must be after started_at")
        return v


class ProductionRunCreateRequest(BaseModel):
    """Schema for production run creation request with items and materials.

    Supports two creation modes:
    - Legacy item-based: Use items[] and materials[] (existing flow)
    - Multi-plate: Use printer_id, product_id, and plates[] (new flow)
    """

    # Main production run data (spread all fields)
    run_number: Optional[str] = Field(None, min_length=1, max_length=50)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = None
    duration_hours: Optional[Decimal] = Field(None, ge=0)
    estimated_print_time_hours: Optional[Decimal] = Field(None, ge=0)
    estimated_model_weight_grams: Optional[Decimal] = Field(None, ge=0)
    estimated_flushed_grams: Optional[Decimal] = Field(None, ge=0)
    estimated_tower_grams: Optional[Decimal] = Field(None, ge=0)
    estimated_total_weight_grams: Optional[Decimal] = Field(None, ge=0)
    actual_model_weight_grams: Optional[Decimal] = Field(None, ge=0)
    actual_flushed_grams: Optional[Decimal] = Field(None, ge=0)
    actual_tower_grams: Optional[Decimal] = Field(None, ge=0)
    actual_total_weight_grams: Optional[Decimal] = Field(None, ge=0)
    waste_filament_grams: Optional[Decimal] = Field(None, ge=0)
    waste_reason: Optional[str] = None
    slicer_software: Optional[str] = Field(None, max_length=100)
    printer_name: Optional[str] = Field(None, max_length=100)
    bed_temperature: Optional[int] = Field(None, ge=0, le=200)
    nozzle_temperature: Optional[int] = Field(None, ge=0, le=500)
    status: Literal["in_progress", "completed", "failed", "cancelled"] = Field("in_progress")
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    quality_notes: Optional[str] = None
    original_run_id: Optional[UUID] = None
    is_reprint: bool = False
    notes: Optional[str] = None

    # Multi-plate run support (new fields)
    printer_id: Optional[UUID] = Field(
        None, description="Primary printer for this run (multi-plate mode)"
    )
    product_id: Optional[UUID] = Field(
        None, description="Product being produced (multi-plate mode)"
    )

    # Nested items and materials (legacy mode)
    items: list["ProductionRunItemCreate"] = Field(default_factory=list)
    materials: list["ProductionRunMaterialCreate"] = Field(default_factory=list)

    # Nested plates (multi-plate mode) - imported at runtime to avoid circular import
    plates: list["ProductionRunPlateCreate"] = Field(
        default_factory=list, description="Plates for multi-plate runs"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure completed_at is after started_at if provided."""
        if v and "started_at" in info.data and info.data["started_at"]:
            started_at = info.data["started_at"]
            if v < started_at:
                raise ValueError("completed_at must be after started_at")
        return v


class ProductionRunUpdate(BaseModel):
    """Schema for updating a production run (all fields optional)."""

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_hours: Optional[Decimal] = Field(None, ge=0)

    # Slicer estimates - split by type
    estimated_print_time_hours: Optional[Decimal] = Field(None, ge=0)
    estimated_model_weight_grams: Optional[Decimal] = Field(None, ge=0)
    estimated_flushed_grams: Optional[Decimal] = Field(None, ge=0)
    estimated_tower_grams: Optional[Decimal] = Field(None, ge=0)
    estimated_total_weight_grams: Optional[Decimal] = Field(None, ge=0)

    # Actual usage - split by type
    actual_model_weight_grams: Optional[Decimal] = Field(None, ge=0)
    actual_flushed_grams: Optional[Decimal] = Field(None, ge=0)
    actual_tower_grams: Optional[Decimal] = Field(None, ge=0)
    actual_total_weight_grams: Optional[Decimal] = Field(None, ge=0)

    # Waste tracking
    waste_filament_grams: Optional[Decimal] = Field(None, ge=0)
    waste_reason: Optional[str] = None

    # Metadata
    slicer_software: Optional[str] = Field(None, max_length=100)
    printer_name: Optional[str] = Field(None, max_length=100)
    bed_temperature: Optional[int] = Field(None, ge=0, le=200)
    nozzle_temperature: Optional[int] = Field(None, ge=0, le=500)

    # Status
    status: Optional[Literal["in_progress", "completed", "failed", "cancelled"]] = None

    # Quality & failure tracking
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    quality_notes: Optional[str] = None

    # Reprint tracking
    original_run_id: Optional[UUID] = None
    is_reprint: Optional[bool] = None

    # Notes
    notes: Optional[str] = None

    @field_validator("completed_at")
    @classmethod
    def validate_completed_at(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure completed_at is after started_at if both provided."""
        if v and "started_at" in info.data and info.data["started_at"]:
            started_at = info.data["started_at"]
            if v < started_at:
                raise ValueError("completed_at must be after started_at")
        return v


class ProductionRunResponse(ProductionRunBase):
    """Schema for production run responses (without nested items/materials)."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    # Multi-plate run fields
    printer_id: Optional[UUID] = Field(None, description="Primary printer for this run")
    product_id: Optional[UUID] = Field(None, description="Product being produced")
    total_plates: int = Field(0, ge=0, description="Total number of plates in this run")
    completed_plates: int = Field(0, ge=0, description="Number of plates completed")

    # Cost analysis (calculated on completion)
    cost_per_gram_actual: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Actual cost per gram = total_material_cost / successful_weight",
    )
    successful_weight_grams: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Total theoretical weight of successful items (for cost calculation)",
    )

    # Summary field for list display
    items_summary: Optional[str] = Field(
        None, description="Summary of items/product for list display"
    )

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def is_multi_plate(self) -> bool:
        """Check if this is a multi-plate run (vs legacy item-based run)."""
        return self.total_plates > 0

    @computed_field
    @property
    def plates_progress_percentage(self) -> float:
        """Calculate plate completion progress as percentage."""
        if self.total_plates == 0:
            return 0.0
        return (self.completed_plates / self.total_plates) * 100.0

    @computed_field
    @property
    def is_all_plates_complete(self) -> bool:
        """Check if all plates are complete."""
        return self.is_multi_plate and self.completed_plates >= self.total_plates

    @computed_field
    @property
    def variance_grams(self) -> Optional[float]:
        """Calculate variance in grams between actual and estimated total usage."""
        if (
            self.actual_total_weight_grams is not None
            and self.estimated_total_weight_grams is not None
        ):
            return float(self.actual_total_weight_grams - self.estimated_total_weight_grams)
        return None

    @computed_field
    @property
    def variance_percentage(self) -> Optional[float]:
        """Calculate variance as percentage of estimated."""
        if (
            self.actual_total_weight_grams is not None
            and self.estimated_total_weight_grams is not None
        ):
            if self.estimated_total_weight_grams > 0:
                variance = self.actual_total_weight_grams - self.estimated_total_weight_grams
                return float((variance / self.estimated_total_weight_grams) * Decimal("100"))
        return None

    @computed_field
    @property
    def time_variance_hours(self) -> Optional[float]:
        """Calculate time variance between actual and estimated print time."""
        if self.duration_hours is not None and self.estimated_print_time_hours is not None:
            return float(self.duration_hours - self.estimated_print_time_hours)
        return None

    @computed_field
    @property
    def time_variance_percentage(self) -> Optional[float]:
        """Calculate time variance as percentage."""
        if (
            self.time_variance_hours is not None
            and self.estimated_print_time_hours is not None
            and self.estimated_print_time_hours > 0
        ):
            return float(
                (Decimal(str(self.time_variance_hours)) / self.estimated_print_time_hours)
                * Decimal("100")
            )
        return None


class ProductionRunDetailResponse(ProductionRunResponse):
    """Schema for detailed production run response (with items, materials, and plates).

    For multi-plate runs (is_multi_plate=True), use the plates field.
    For legacy runs (is_multi_plate=False), use the items field.
    """

    items: list[ProductionRunItemResponse] = Field(
        default_factory=list, description="Items printed in this run (legacy mode)"
    )
    materials: list[ProductionRunMaterialResponse] = Field(
        default_factory=list, description="Materials used in this run"
    )

    # Multi-plate run data
    plates: list["ProductionRunPlateResponse"] = Field(
        default_factory=list, description="Plates in this run (multi-plate mode)"
    )

    # Nested summaries for multi-plate runs (optional, may not always be loaded)
    printer: Optional["PrinterSummary"] = Field(None, description="Printer details")
    product: Optional[ProductSummary] = Field(None, description="Product details")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def total_items_planned(self) -> int:
        """Calculate total items planned across all products."""
        return sum(item.quantity for item in self.items)

    @computed_field
    @property
    def total_items_successful(self) -> int:
        """Calculate total successful items across all products."""
        return sum(item.successful_quantity for item in self.items)

    @computed_field
    @property
    def total_items_failed(self) -> int:
        """Calculate total failed items across all products."""
        return sum(item.failed_quantity for item in self.items)

    @computed_field
    @property
    def overall_success_rate(self) -> Optional[float]:
        """Calculate overall success rate across all items."""
        total_planned = self.total_items_planned
        if total_planned > 0:
            return float(
                (Decimal(str(self.total_items_successful)) / Decimal(str(total_planned)))
                * Decimal("100")
            )
        return None

    @computed_field
    @property
    def total_material_cost(self) -> float:
        """Calculate total material cost from all materials."""
        return float(sum(material.total_cost for material in self.materials))

    @computed_field
    @property
    def total_estimated_cost(self) -> float:
        """Calculate total estimated cost from all items."""
        return float(sum(item.estimated_total_cost or Decimal("0") for item in self.items))


class ProductionRunListResponse(BaseModel):
    """Schema for paginated production run list."""

    runs: list[ProductionRunResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


# Production Run Item Schemas
class ProductionRunItemBase(BaseModel):
    """Base schema for production run items."""

    model_id: UUID = Field(..., description="Model ID (the 3D model being printed)")
    quantity: int = Field(..., gt=0, description="Planned quantity to print")
    bed_position: Optional[str] = Field(None, max_length=50, description="Position on print bed")

    # Estimated costs (captured from product BOM at creation time)
    estimated_material_cost: Optional[Decimal] = Field(
        None, ge=0, description="Estimated material cost"
    )
    estimated_component_cost: Optional[Decimal] = Field(
        None, ge=0, description="Estimated component cost"
    )
    estimated_labor_cost: Optional[Decimal] = Field(None, ge=0, description="Estimated labor cost")
    estimated_total_cost: Optional[Decimal] = Field(None, ge=0, description="Estimated total cost")

    # Notes
    notes: Optional[str] = Field(None, description="Item-specific notes")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Ensure quantity is positive."""
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class ProductionRunItemCreate(ProductionRunItemBase):
    """Schema for creating a production run item."""

    # Optional: Can be provided if quantities are known at creation
    successful_quantity: Optional[int] = Field(
        None, ge=0, description="Successful quantity if known"
    )
    failed_quantity: Optional[int] = Field(None, ge=0, description="Failed quantity if known")


class ProductionRunItemUpdate(BaseModel):
    """Schema for updating a production run item (all fields optional)."""

    model_id: Optional[UUID] = None
    quantity: Optional[int] = Field(None, gt=0)
    successful_quantity: Optional[int] = Field(None, ge=0)
    failed_quantity: Optional[int] = Field(None, ge=0)
    bed_position: Optional[str] = Field(None, max_length=50)
    estimated_material_cost: Optional[Decimal] = Field(None, ge=0)
    estimated_component_cost: Optional[Decimal] = Field(None, ge=0)
    estimated_labor_cost: Optional[Decimal] = Field(None, ge=0)
    estimated_total_cost: Optional[Decimal] = Field(None, ge=0)
    notes: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[int]) -> Optional[int]:
        """Ensure quantity is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("successful_quantity", "failed_quantity")
    @classmethod
    def validate_quantities_non_negative(cls, v: Optional[int]) -> Optional[int]:
        """Ensure quantities are non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Quantities must be non-negative")
        return v


class ProductionRunItemResponse(ProductionRunItemBase):
    """Schema for production run item responses."""

    id: UUID
    production_run_id: UUID
    successful_quantity: int = Field(default=0, ge=0, description="Successful quantity printed")
    failed_quantity: int = Field(default=0, ge=0, description="Failed quantity")
    created_at: datetime
    updated_at: datetime

    # Cost analysis (calculated on run completion)
    model_weight_grams: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Cached model weight from BOM (for cost calculation)",
    )
    actual_cost_per_unit: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Actual cost per unit = model_weight × cost_per_gram_actual",
    )

    # Nested model details (populated via relationship)
    # Note: We use "model" field name to match SQLAlchemy relationship
    model: Optional[ModelSummary] = Field(default=None, description="Model details")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def success_rate(self) -> Optional[float]:
        """Calculate success rate as percentage."""
        if self.quantity > 0:
            return float(
                (Decimal(str(self.successful_quantity)) / Decimal(str(self.quantity)))
                * Decimal("100")
            )
        return None

    @computed_field
    @property
    def total_quantity_accounted(self) -> int:
        """Calculate total quantity accounted for (successful + failed)."""
        return self.successful_quantity + self.failed_quantity

    @computed_field
    @property
    def unaccounted_quantity(self) -> int:
        """Calculate unaccounted quantity (planned - accounted)."""
        return self.quantity - self.total_quantity_accounted


# Production Run Material Schemas
class ProductionRunMaterialBase(BaseModel):
    """Base schema for production run materials."""

    spool_id: UUID = Field(..., description="Spool ID (filament spool used)")
    # Estimated weights - split by type
    estimated_model_weight_grams: Decimal = Field(
        ..., gt=0, description="Estimated model weight from this spool"
    )
    estimated_flushed_grams: Decimal = Field(
        Decimal("0"), ge=0, description="Estimated purge/flush from this spool"
    )
    estimated_tower_grams: Decimal = Field(
        Decimal("0"), ge=0, description="Estimated tower weight from this spool"
    )
    cost_per_gram: Decimal = Field(..., gt=0, description="Cost per gram (captured from spool)")

    @field_validator("estimated_model_weight_grams", "cost_per_gram")
    @classmethod
    def validate_positive_decimals(cls, v: Decimal) -> Decimal:
        """Ensure weight and cost values are positive."""
        if v <= 0:
            raise ValueError("Value must be greater than 0")
        return v

    @field_validator("estimated_flushed_grams", "estimated_tower_grams")
    @classmethod
    def validate_non_negative_decimal(cls, v: Decimal) -> Decimal:
        """Ensure values are non-negative."""
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v


class ProductionRunMaterialCreate(ProductionRunMaterialBase):
    """Schema for creating a production run material."""

    # Optional: Spool weighing (can be provided if known at creation)
    spool_weight_before_grams: Optional[Decimal] = Field(None, ge=0)
    spool_weight_after_grams: Optional[Decimal] = Field(None, ge=0)

    # Optional: Actual usage - split by type (can be provided if known at creation)
    actual_model_weight_grams: Optional[Decimal] = Field(None, ge=0)
    actual_flushed_grams: Optional[Decimal] = Field(None, ge=0)
    actual_tower_grams: Optional[Decimal] = Field(None, ge=0)


class ProductionRunMaterialUpdate(BaseModel):
    """Schema for updating a production run material (all fields optional)."""

    spool_id: Optional[UUID] = None
    # Estimated weights - split by type
    estimated_model_weight_grams: Optional[Decimal] = Field(None, gt=0)
    estimated_flushed_grams: Optional[Decimal] = Field(None, ge=0)
    estimated_tower_grams: Optional[Decimal] = Field(None, ge=0)

    # Spool weighing (before/after print)
    spool_weight_before_grams: Optional[Decimal] = Field(None, ge=0)
    spool_weight_after_grams: Optional[Decimal] = Field(None, ge=0)

    # Actual usage - split by type
    actual_model_weight_grams: Optional[Decimal] = Field(None, ge=0)
    actual_flushed_grams: Optional[Decimal] = Field(None, ge=0)
    actual_tower_grams: Optional[Decimal] = Field(None, ge=0)

    cost_per_gram: Optional[Decimal] = Field(None, gt=0)

    @field_validator("estimated_model_weight_grams", "cost_per_gram")
    @classmethod
    def validate_positive_decimals(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure weight and cost values are positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Value must be greater than 0")
        return v

    @field_validator(
        "estimated_flushed_grams",
        "estimated_tower_grams",
        "spool_weight_before_grams",
        "spool_weight_after_grams",
        "actual_model_weight_grams",
        "actual_flushed_grams",
        "actual_tower_grams",
    )
    @classmethod
    def validate_non_negative_decimals(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure values are non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Value must be non-negative")
        return v


class ProductionRunMaterialResponse(ProductionRunMaterialBase):
    """Schema for production run material responses."""

    id: UUID
    production_run_id: UUID

    # Spool weighing (before/after print)
    spool_weight_before_grams: Optional[Decimal] = None
    spool_weight_after_grams: Optional[Decimal] = None

    # Actual usage - split by type
    actual_model_weight_grams: Optional[Decimal] = None
    actual_flushed_grams: Optional[Decimal] = None
    actual_tower_grams: Optional[Decimal] = None

    created_at: datetime
    updated_at: datetime

    # Nested spool details (populated via relationship)
    spool: Optional[SpoolSummary] = Field(None, description="Spool details")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def estimated_total_weight(self) -> float:
        """Calculate total estimated weight (model + flushed + tower)."""
        return float(
            self.estimated_model_weight_grams
            + self.estimated_flushed_grams
            + self.estimated_tower_grams
        )

    @computed_field
    @property
    def actual_weight_from_weighing(self) -> Optional[float]:
        """Calculate actual weight from spool weighing."""
        if self.spool_weight_before_grams is not None and self.spool_weight_after_grams is not None:
            return float(self.spool_weight_before_grams - self.spool_weight_after_grams)
        return None

    @computed_field
    @property
    def actual_total_weight(self) -> float:
        """Get total actual weight (from weighing or manual split totals)."""
        if self.actual_weight_from_weighing is not None:
            return self.actual_weight_from_weighing
        return float(
            (self.actual_model_weight_grams or Decimal("0"))
            + (self.actual_flushed_grams or Decimal("0"))
            + (self.actual_tower_grams or Decimal("0"))
        )

    @computed_field
    @property
    def variance_grams(self) -> float:
        """Calculate variance between actual and estimated total."""
        return self.actual_total_weight - self.estimated_total_weight

    @computed_field
    @property
    def variance_percentage(self) -> float:
        """Calculate variance as percentage of estimated."""
        est_weight = (
            self.estimated_model_weight_grams
            + self.estimated_flushed_grams
            + self.estimated_tower_grams
        )
        if est_weight > 0:
            return float((Decimal(str(self.variance_grams)) / est_weight) * Decimal("100"))
        return 0.0

    @computed_field
    @property
    def estimated_cost(self) -> float:
        """Calculate estimated cost based on estimated weight."""
        return float(Decimal(str(self.estimated_total_weight)) * self.cost_per_gram)

    @computed_field
    @property
    def total_cost(self) -> float:
        """Calculate total cost of material used (actual)."""
        return float(Decimal(str(self.actual_total_weight)) * self.cost_per_gram)


# Cancel and Fail Operation Schemas
class MaterialUsageEntry(BaseModel):
    """Entry for specifying material usage per spool."""

    spool_id: UUID = Field(..., description="Spool ID")
    grams: Decimal = Field(..., ge=0, description="Grams of filament used/wasted")


class CancelProductionRunRequest(BaseModel):
    """Schema for cancelling a production run."""

    cancel_mode: str = Field(
        "full_reversal",
        description="Cancel mode: 'full_reversal' (restore spools) or 'record_partial' (deduct actual usage)",
    )
    partial_usage: list[MaterialUsageEntry] = Field(
        default_factory=list,
        description="Actual usage per spool when cancel_mode is 'record_partial'",
    )

    @field_validator("cancel_mode")
    @classmethod
    def validate_cancel_mode(cls, v: str) -> str:
        """Validate cancel mode is valid."""
        allowed = ["full_reversal", "record_partial"]
        if v not in allowed:
            raise ValueError(f"cancel_mode must be one of: {', '.join(allowed)}")
        return v


class FailProductionRunRequest(BaseModel):
    """Schema for marking a production run as failed with waste tracking."""

    failure_reason: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Reason for failure (e.g., 'spaghetti', 'layer_shift', 'clog', 'adhesion', 'stringing')",
    )
    waste_materials: list[MaterialUsageEntry] = Field(
        ..., min_length=1, description="Wasted filament per spool (at least one entry required)"
    )
    notes: Optional[str] = Field(
        None, max_length=1000, description="Additional notes about the failure"
    )

    @field_validator("failure_reason")
    @classmethod
    def validate_failure_reason(cls, v: str) -> str:
        """Validate and normalize failure reason."""
        return v.strip().lower()


class FailureReasonOption(BaseModel):
    """Schema for predefined failure reason options."""

    value: str
    label: str
    description: Optional[str] = None


# Predefined failure reasons for UI
FAILURE_REASONS: list[FailureReasonOption] = [
    FailureReasonOption(
        value="spaghetti",
        label="Spaghetti",
        description="Print detached and became tangled filament",
    ),
    FailureReasonOption(
        value="layer_shift", label="Layer Shift", description="Layers misaligned during print"
    ),
    FailureReasonOption(
        value="adhesion", label="Bed Adhesion", description="Print detached from build plate"
    ),
    FailureReasonOption(
        value="clog", label="Nozzle Clog", description="Nozzle became clogged during print"
    ),
    FailureReasonOption(
        value="stringing", label="Stringing", description="Excessive stringing between parts"
    ),
    FailureReasonOption(value="warping", label="Warping", description="Print warped or curled"),
    FailureReasonOption(
        value="under_extrusion", label="Under Extrusion", description="Not enough material extruded"
    ),
    FailureReasonOption(
        value="over_extrusion", label="Over Extrusion", description="Too much material extruded"
    ),
    FailureReasonOption(
        value="power_failure", label="Power Failure", description="Power outage interrupted print"
    ),
    FailureReasonOption(
        value="filament_runout",
        label="Filament Runout",
        description="Ran out of filament mid-print",
    ),
    FailureReasonOption(value="other", label="Other", description="Other failure reason"),
]


# Rebuild models to resolve forward references
# This is required because we use TYPE_CHECKING imports for circular dependency avoidance
def _rebuild_models() -> None:
    """Rebuild models to resolve forward references after all schemas are defined."""
    # Late import to avoid circular dependency and provide types for model_rebuild
    from app.schemas.printer import PrinterSummary
    from app.schemas.production_run_plate import (
        ProductionRunPlateCreate,
        ProductionRunPlateResponse,
    )

    ProductionRunCreateRequest.model_rebuild(
        _types_namespace={
            "ProductionRunPlateCreate": ProductionRunPlateCreate,
        }
    )
    ProductionRunDetailResponse.model_rebuild(
        _types_namespace={
            "ProductionRunPlateResponse": ProductionRunPlateResponse,
            "PrinterSummary": PrinterSummary,
        }
    )


_rebuild_models()
