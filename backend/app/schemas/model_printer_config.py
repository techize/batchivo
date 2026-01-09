"""Pydantic schemas for ModelPrinterConfig API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.printer import PrinterSummary
from app.schemas.production_run import ModelSummary


class ModelPrinterConfigBase(BaseModel):
    """Base schema for model printer configuration."""

    # Print settings
    prints_per_plate: int = Field(
        1, ge=1, description="How many of this model fit on one plate for this printer"
    )
    print_time_minutes: Optional[int] = Field(
        None, ge=1, description="Total print time for full plate (all prints_per_plate items)"
    )
    material_weight_grams: Optional[Decimal] = Field(
        None, ge=Decimal("0.01"), description="Material weight for ONE item (not full plate)"
    )

    # Temperature settings
    bed_temperature: Optional[int] = Field(
        None, ge=0, le=200, description="Bed temperature for this model on this printer"
    )
    nozzle_temperature: Optional[int] = Field(
        None, ge=0, le=500, description="Nozzle temperature for this model on this printer"
    )

    # Slicer settings
    layer_height: Optional[Decimal] = Field(
        None, ge=Decimal("0.04"), le=Decimal("1.0"), description="Layer height in millimeters"
    )
    infill_percentage: Optional[int] = Field(
        None, ge=0, le=100, description="Infill percentage (0-100)"
    )
    supports: Optional[bool] = Field(False, description="Whether supports are required")
    brim: Optional[bool] = Field(False, description="Whether brim is required")

    # Additional settings
    slicer_settings: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Additional slicer settings (speed, retraction, etc.)"
    )

    # Notes
    notes: Optional[str] = Field(None, description="Configuration notes")

    @field_validator("prints_per_plate")
    @classmethod
    def validate_prints_per_plate(cls, v: int) -> int:
        """Ensure prints_per_plate is at least 1."""
        if v < 1:
            raise ValueError("prints_per_plate must be at least 1")
        return v


class ModelPrinterConfigCreate(ModelPrinterConfigBase):
    """Schema for creating a model printer configuration."""

    model_id: UUID = Field(..., description="Model this config applies to")
    printer_id: UUID = Field(..., description="Printer this config is for")


class ModelPrinterConfigUpdate(BaseModel):
    """Schema for updating a model printer configuration (all fields optional)."""

    prints_per_plate: Optional[int] = Field(None, ge=1)
    print_time_minutes: Optional[int] = Field(None, ge=1)
    material_weight_grams: Optional[Decimal] = Field(None, ge=Decimal("0.01"))

    bed_temperature: Optional[int] = Field(None, ge=0, le=200)
    nozzle_temperature: Optional[int] = Field(None, ge=0, le=500)

    layer_height: Optional[Decimal] = Field(None, ge=Decimal("0.04"), le=Decimal("1.0"))
    infill_percentage: Optional[int] = Field(None, ge=0, le=100)
    supports: Optional[bool] = None
    brim: Optional[bool] = None

    slicer_settings: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class ModelPrinterConfigResponse(ModelPrinterConfigBase):
    """Schema for model printer configuration responses."""

    id: UUID
    model_id: UUID
    printer_id: UUID
    created_at: datetime
    updated_at: datetime

    # Nested relationship data (optional, may not always be loaded)
    model: Optional[ModelSummary] = Field(None, description="Model details")
    printer: Optional[PrinterSummary] = Field(None, description="Printer details")

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def print_time_per_item_minutes(self) -> Optional[int]:
        """Calculate print time per individual item."""
        if self.print_time_minutes and self.prints_per_plate:
            return self.print_time_minutes // self.prints_per_plate
        return None

    @computed_field
    @property
    def material_weight_per_plate_grams(self) -> Optional[float]:
        """Calculate total material weight for a full plate."""
        if self.material_weight_grams and self.prints_per_plate:
            return float(self.material_weight_grams * self.prints_per_plate)
        return None


class ModelPrinterConfigSummary(BaseModel):
    """Lightweight summary for embedding in other responses."""

    id: UUID
    printer_id: UUID
    prints_per_plate: int
    print_time_minutes: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ModelPrinterConfigListResponse(BaseModel):
    """Schema for paginated config list."""

    configs: list[ModelPrinterConfigResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
