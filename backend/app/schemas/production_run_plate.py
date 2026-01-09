"""Pydantic schemas for ProductionRunPlate API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.printer import PrinterSummary
from app.schemas.production_run import ModelSummary


# Plate status type
PlateStatus = Literal["pending", "printing", "complete", "failed", "cancelled"]


class ProductionRunPlateBase(BaseModel):
    """Base schema for production run plates."""

    plate_number: int = Field(..., ge=1, description="Plate number for ordering (1, 2, 3...)")
    plate_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Plate name (e.g., 'Dragon Bodies (A1 Mini)')",
    )

    # Quantity tracking
    quantity: int = Field(1, ge=1, description="How many times this plate needs to be printed")
    prints_per_plate: int = Field(
        ..., ge=1, description="How many items per single plate (e.g., 3 dragons per plate)"
    )

    # Estimates
    print_time_minutes: Optional[int] = Field(
        None, ge=1, description="Estimated print time per plate"
    )
    estimated_material_weight_grams: Optional[Decimal] = Field(
        None, ge=Decimal("0.01"), description="Estimated material weight per plate"
    )

    # Notes
    notes: Optional[str] = Field(None, description="Plate-specific notes")

    @field_validator("plate_number")
    @classmethod
    def validate_plate_number(cls, v: int) -> int:
        """Ensure plate_number is positive."""
        if v < 1:
            raise ValueError("plate_number must be at least 1")
        return v

    @field_validator("quantity", "prints_per_plate")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Ensure quantity and prints_per_plate are positive."""
        if v < 1:
            raise ValueError("Value must be at least 1")
        return v


class ProductionRunPlateCreate(ProductionRunPlateBase):
    """Schema for creating a production run plate."""

    model_id: UUID = Field(..., description="Model being printed on this plate")
    printer_id: UUID = Field(..., description="Printer for this plate")

    # Status defaults to pending for new plates
    status: PlateStatus = Field("pending", description="Plate status")


class ProductionRunPlateUpdate(BaseModel):
    """Schema for updating a production run plate (for marking complete, etc.)."""

    # Status updates
    status: Optional[PlateStatus] = Field(None, description="Plate status")

    # Timing
    started_at: Optional[datetime] = Field(None, description="When plate printing started")
    completed_at: Optional[datetime] = Field(None, description="When plate printing completed")

    # Actuals
    actual_print_time_minutes: Optional[int] = Field(None, ge=0, description="Actual print time")
    actual_material_weight_grams: Optional[Decimal] = Field(
        None, ge=Decimal("0"), description="Actual material used"
    )

    # Print results
    successful_prints: Optional[int] = Field(
        None, ge=0, description="Number of successful prints from this plate"
    )
    failed_prints: Optional[int] = Field(
        None, ge=0, description="Number of failed prints from this plate"
    )

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


class ProductionRunPlateResponse(ProductionRunPlateBase):
    """Schema for production run plate responses."""

    id: UUID
    production_run_id: UUID
    model_id: UUID
    printer_id: UUID

    # Status
    status: PlateStatus

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Actuals
    actual_print_time_minutes: Optional[int] = None
    actual_material_weight_grams: Optional[Decimal] = None

    # Print results
    successful_prints: int = 0
    failed_prints: int = 0

    # Cost analysis (calculated on run completion)
    model_weight_grams: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        description="Cached model weight from BOM (for cost calculation)",
    )
    actual_cost_per_unit: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        description="Actual cost per unit = model_weight × cost_per_gram_actual",
    )

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Nested relationship data (optional)
    model: Optional[ModelSummary] = Field(None, description="Model details")
    printer: Optional[PrinterSummary] = Field(None, description="Printer details")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def is_complete(self) -> bool:
        """Check if plate is complete."""
        return self.status == "complete"

    @computed_field
    @property
    def is_pending(self) -> bool:
        """Check if plate is pending."""
        return self.status == "pending"

    @computed_field
    @property
    def is_printing(self) -> bool:
        """Check if plate is currently printing."""
        return self.status == "printing"

    @computed_field
    @property
    def total_items_expected(self) -> int:
        """Calculate total items expected from this plate (quantity x prints_per_plate)."""
        return self.quantity * self.prints_per_plate

    @computed_field
    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage (based on successful prints vs expected)."""
        expected = self.total_items_expected
        if expected == 0:
            return 0.0
        return (self.successful_prints / expected) * 100.0

    @computed_field
    @property
    def total_estimated_time_minutes(self) -> Optional[int]:
        """Calculate total estimated time for all prints of this plate."""
        if self.print_time_minutes and self.quantity:
            return self.print_time_minutes * self.quantity
        return None

    @computed_field
    @property
    def total_estimated_material_grams(self) -> Optional[float]:
        """Calculate total estimated material for all prints of this plate."""
        if self.estimated_material_weight_grams and self.quantity:
            return float(self.estimated_material_weight_grams * self.quantity)
        return None


class ProductionRunPlateSummary(BaseModel):
    """Lightweight plate summary for lists."""

    id: UUID
    plate_number: int
    plate_name: str
    status: PlateStatus
    quantity: int
    prints_per_plate: int
    successful_prints: int = 0
    failed_prints: int = 0

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def total_items_expected(self) -> int:
        """Calculate total items expected from this plate."""
        return self.quantity * self.prints_per_plate

    @computed_field
    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage."""
        expected = self.total_items_expected
        if expected == 0:
            return 0.0
        return (self.successful_prints / expected) * 100.0


class ProductionRunPlateListResponse(BaseModel):
    """Schema for paginated plate list."""

    plates: list[ProductionRunPlateResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


class MarkPlateCompleteRequest(BaseModel):
    """Schema for marking a plate as complete."""

    actual_print_time_minutes: Optional[int] = Field(None, ge=0, description="Actual print time")
    actual_material_weight_grams: Optional[Decimal] = Field(
        None, ge=Decimal("0"), description="Actual material used"
    )
    successful_prints: int = Field(
        ..., ge=0, description="Number of successful prints from this plate"
    )
    failed_prints: int = Field(0, ge=0, description="Number of failed prints from this plate")
    notes: Optional[str] = Field(None, description="Completion notes")
