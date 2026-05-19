"""Pydantic schemas for Spool API."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.filament_type import FilamentTypeResponse


# Base schema with common fields
class SpoolBase(BaseModel):
    """Base spool schema with common fields."""

    spool_id: str = Field(..., min_length=1, max_length=50, description="User-friendly spool ID")
    filament_type_id: UUID = Field(..., description="FilamentType ID")

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

    # Organization
    storage_location: Optional[str] = Field(None, max_length=100, description="Storage location")
    qr_code_id: Optional[str] = Field(None, max_length=100, description="QR code ID")
    is_active: bool = Field(True, description="Whether spool is active")
    is_labeled: bool = Field(False, description="Whether a label has been printed for this spool")


# Create schema (for POST requests)
class SpoolCreate(SpoolBase):
    """Schema for creating a new spool."""

    pass  # Inherits all fields from SpoolBase


# Update schema (for PUT/PATCH requests)
class SpoolUpdate(BaseModel):
    """Schema for updating a spool (all fields optional)."""

    spool_id: Optional[str] = Field(None, min_length=1, max_length=50)
    filament_type_id: Optional[UUID] = None

    # Weight tracking
    initial_weight: Optional[float] = Field(None, gt=0)
    current_weight: Optional[float] = Field(None, ge=0)
    empty_spool_weight: Optional[float] = Field(None, ge=0)

    # Purchase info
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = Field(None, max_length=100)

    # Organization
    storage_location: Optional[str] = Field(None, max_length=100)
    qr_code_id: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    is_labeled: Optional[bool] = None


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

    # FilamentType info (nested)
    filament_type: Optional["FilamentTypeResponse"] = None

    model_config = ConfigDict(from_attributes=True)


# List response schema
class SpoolListResponse(BaseModel):
    """Schema for paginated spool list."""

    total: int = Field(..., description="Total number of spools")
    spools: list[SpoolResponse] = Field(..., description="List of spools")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
