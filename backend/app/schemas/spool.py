"""Pydantic schemas for Spool API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Base schema with common fields
class SpoolBase(BaseModel):
    """Base spool schema with common fields."""

    spool_id: str = Field(..., min_length=1, max_length=50, description="User-friendly spool ID")
    material_type_id: UUID = Field(..., description="Material type ID (PLA, PETG, etc.)")
    brand: str = Field(..., min_length=1, max_length=100, description="Filament brand")
    color: str = Field(..., min_length=1, max_length=50, description="Filament color")
    color_hex: Optional[str] = Field(
        None, max_length=9, description="Hex color code (e.g., FF5733)"
    )
    finish: Optional[str] = Field(
        None, max_length=50, description="Finish type (matte, glossy, etc.)"
    )

    # Filament specifications
    diameter: float = Field(1.75, gt=0, le=5, description="Filament diameter in mm")
    density: Optional[float] = Field(None, gt=0, le=10, description="Filament density in g/cm³")
    extruder_temp: Optional[int] = Field(
        None, ge=150, le=400, description="Recommended extruder temp °C"
    )
    bed_temp: Optional[int] = Field(None, ge=0, le=150, description="Recommended bed temp °C")

    # Special filament properties
    translucent: bool = Field(False, description="Whether filament is translucent")
    glow: bool = Field(False, description="Whether filament is glow-in-the-dark")
    pattern: Optional[str] = Field(None, max_length=50, description="Pattern type (marble, etc.)")
    spool_type: Optional[str] = Field(
        None, max_length=50, description="Spool type (cardboard, plastic, etc.)"
    )

    # Weight tracking
    initial_weight: float = Field(..., gt=0, description="Initial filament weight in grams")
    current_weight: float = Field(..., ge=0, description="Current filament weight in grams")
    empty_spool_weight: Optional[float] = Field(
        None, ge=0, description="Weight of empty spool in grams"
    )

    # Purchase info
    purchase_date: Optional[datetime] = Field(None, description="Purchase date")
    purchase_price: Optional[float] = Field(None, ge=0, description="Purchase price")
    supplier: Optional[str] = Field(None, max_length=100, description="Supplier name")

    # Batch tracking
    purchased_quantity: int = Field(1, ge=1, description="Number of spools purchased in this batch")
    spools_remaining: int = Field(1, ge=1, description="Number of spools remaining from this batch")

    # Organization
    storage_location: Optional[str] = Field(None, max_length=100, description="Storage location")
    notes: Optional[str] = Field(None, description="Additional notes")
    qr_code_id: Optional[str] = Field(None, max_length=100, description="QR code ID")
    is_active: bool = Field(True, description="Whether spool is active")


# Create schema (for POST requests)
class SpoolCreate(SpoolBase):
    """Schema for creating a new spool."""

    pass  # Inherits all fields from SpoolBase


# Update schema (for PUT/PATCH requests)
class SpoolUpdate(BaseModel):
    """Schema for updating a spool (all fields optional)."""

    spool_id: Optional[str] = Field(None, min_length=1, max_length=50)
    material_type_id: Optional[UUID] = None
    brand: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, min_length=1, max_length=50)
    color_hex: Optional[str] = Field(None, max_length=9)
    finish: Optional[str] = Field(None, max_length=50)

    # Filament specifications
    diameter: Optional[float] = Field(None, gt=0, le=5)
    density: Optional[float] = Field(None, gt=0, le=10)
    extruder_temp: Optional[int] = Field(None, ge=150, le=400)
    bed_temp: Optional[int] = Field(None, ge=0, le=150)

    # Special filament properties
    translucent: Optional[bool] = None
    glow: Optional[bool] = None
    pattern: Optional[str] = Field(None, max_length=50)
    spool_type: Optional[str] = Field(None, max_length=50)

    # Weight tracking
    initial_weight: Optional[float] = Field(None, gt=0)
    current_weight: Optional[float] = Field(None, ge=0)
    empty_spool_weight: Optional[float] = Field(None, ge=0)

    # Purchase info
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = Field(None, max_length=100)

    # Batch tracking
    purchased_quantity: Optional[int] = Field(None, ge=1)
    spools_remaining: Optional[int] = Field(None, ge=1)

    # Organization
    storage_location: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    qr_code_id: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


# Response schema (for GET responses)
class SpoolResponse(SpoolBase):
    """Schema for spool responses."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    # Computed fields
    remaining_weight: float = Field(..., description="Remaining weight in grams")
    remaining_percentage: float = Field(..., description="Remaining percentage")

    # Material type info (nested)
    material_type_code: str = Field(..., description="Material code (PLA, PETG, etc.)")
    material_type_name: str = Field(..., description="Material name")

    model_config = ConfigDict(from_attributes=True)


# List response schema
class SpoolListResponse(BaseModel):
    """Schema for paginated spool list."""

    total: int = Field(..., description="Total number of spools")
    spools: list[SpoolResponse] = Field(..., description="List of spools")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
