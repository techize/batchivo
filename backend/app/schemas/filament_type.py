"""Pydantic schemas for FilamentType API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FilamentTypeBase(BaseModel):
    """Base FilamentType schema with common fields."""

    material_type_id: UUID = Field(..., description="Material type ID (PLA, PETG, etc.)")
    brand: str = Field(..., min_length=1, max_length=100, description="Filament brand/manufacturer")
    color: str = Field(..., min_length=1, max_length=50, description="Filament colour name")
    color_hex: Optional[str] = Field(
        None, max_length=9, description="Hex colour code (e.g., FF5733 or 00FF5733)"
    )
    finish: Optional[str] = Field(
        None, max_length=50, description="Finish type (matte, glossy, metallic, etc.)"
    )
    pattern: Optional[str] = Field(
        None, max_length=50, description="Pattern type (marble, gradient, speckled, etc.)"
    )
    spool_type: Optional[str] = Field(
        None, max_length=50, description="Spool type (cardboard, plastic, refill, etc.)"
    )

    # Filament specifications
    diameter: float = Field(1.75, gt=0, le=5, description="Filament diameter in mm")
    density: Optional[float] = Field(None, gt=0, le=10, description="Filament density in g/cm³")
    extruder_temp: Optional[int] = Field(
        None, ge=150, le=400, description="Recommended extruder temperature in °C"
    )
    bed_temp: Optional[int] = Field(
        None, ge=0, le=150, description="Recommended bed temperature in °C"
    )

    # Special properties
    translucent: bool = Field(False, description="Whether filament is translucent/transparent")
    glow: bool = Field(False, description="Whether filament is glow-in-the-dark")
    has_sample: bool = Field(
        False, description="Whether a display benchy has been printed for this filament type"
    )

    notes: Optional[str] = Field(None, description="Additional notes about this filament type")


class FilamentTypeCreate(FilamentTypeBase):
    """Schema for creating a new FilamentType."""

    pass


class FilamentTypeUpdate(BaseModel):
    """Schema for updating a FilamentType (all fields optional)."""

    material_type_id: Optional[UUID] = None
    brand: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, min_length=1, max_length=50)
    color_hex: Optional[str] = Field(None, max_length=9)
    finish: Optional[str] = Field(None, max_length=50)
    pattern: Optional[str] = Field(None, max_length=50)
    spool_type: Optional[str] = Field(None, max_length=50)

    # Filament specifications
    diameter: Optional[float] = Field(None, gt=0, le=5)
    density: Optional[float] = Field(None, gt=0, le=10)
    extruder_temp: Optional[int] = Field(None, ge=150, le=400)
    bed_temp: Optional[int] = Field(None, ge=0, le=150)

    # Special properties
    translucent: Optional[bool] = None
    glow: Optional[bool] = None
    has_sample: Optional[bool] = None

    notes: Optional[str] = None


class FilamentTypeResponse(FilamentTypeBase):
    """Schema for FilamentType responses."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    # Denormalised from lazy=joined material_type relationship
    material_type_code: str = Field(..., description="Material code (PLA, PETG, etc.)")
    material_type_name: str = Field(..., description="Material full name")

    model_config = ConfigDict(from_attributes=True)


class FilamentTypeListResponse(BaseModel):
    """Schema for paginated FilamentType list."""

    total: int = Field(..., description="Total number of filament types")
    filament_types: list[FilamentTypeResponse] = Field(..., description="List of filament types")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class FilamentTypeAggregatedResponse(BaseModel):
    """Slim aggregated response for list view — includes spool counts, excludes spec fields."""

    id: UUID
    brand: str
    color: str
    color_hex: Optional[str] = None
    material_type_name: str
    material_type_code: str
    has_sample: bool
    spool_count: int
    labeled_count: int

    model_config = ConfigDict(from_attributes=False)


class FilamentTypeAggregatedListResponse(BaseModel):
    """Paginated aggregated FilamentType list for the list view."""

    total: int = Field(description="Total number of filament types")
    filament_types: list[FilamentTypeAggregatedResponse] = Field(description="Aggregated list")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class SpoolInSheetResponse(BaseModel):
    """Minimal spool info for the read-only spool drill-down sheet."""

    id: UUID
    spool_id: str
    current_weight: float
    initial_weight: float
    is_labeled: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
