"""Pydantic schemas for Printer API."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PrinterBase(BaseModel):
    """Base printer schema with common fields."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Printer name (e.g., 'Bambu A1 Mini')"
    )
    manufacturer: Optional[str] = Field(None, max_length=100, description="Manufacturer name")
    model: Optional[str] = Field(None, max_length=100, description="Model name")

    # Bed size
    bed_size_x_mm: Optional[int] = Field(None, ge=1, description="Bed size X in millimeters")
    bed_size_y_mm: Optional[int] = Field(None, ge=1, description="Bed size Y in millimeters")
    bed_size_z_mm: Optional[int] = Field(None, ge=1, description="Bed size Z in millimeters")

    # Printer settings
    nozzle_diameter_mm: Optional[Decimal] = Field(
        Decimal("0.4"),
        ge=Decimal("0.1"),
        le=Decimal("2.0"),
        description="Nozzle diameter in millimeters",
    )
    default_bed_temp: Optional[int] = Field(
        None, ge=0, le=200, description="Default bed temperature in Celsius"
    )
    default_nozzle_temp: Optional[int] = Field(
        None, ge=0, le=500, description="Default nozzle temperature in Celsius"
    )

    # Capabilities
    capabilities: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Printer capabilities (AMS, materials, etc.)"
    )

    # Status
    is_active: bool = Field(True, description="Whether printer is active")

    # Notes
    notes: Optional[str] = Field(None, description="Additional notes")


class PrinterCreate(PrinterBase):
    """Schema for creating a new printer."""

    pass


class PrinterUpdate(BaseModel):
    """Schema for updating a printer (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)

    bed_size_x_mm: Optional[int] = Field(None, ge=1)
    bed_size_y_mm: Optional[int] = Field(None, ge=1)
    bed_size_z_mm: Optional[int] = Field(None, ge=1)

    nozzle_diameter_mm: Optional[Decimal] = Field(None, ge=Decimal("0.1"), le=Decimal("2.0"))
    default_bed_temp: Optional[int] = Field(None, ge=0, le=200)
    default_nozzle_temp: Optional[int] = Field(None, ge=0, le=500)

    capabilities: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class PrinterResponse(PrinterBase):
    """Schema for printer responses."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def bed_size_str(self) -> Optional[str]:
        """Return bed size as formatted string (e.g., '180x180x180')."""
        if self.bed_size_x_mm and self.bed_size_y_mm and self.bed_size_z_mm:
            return f"{self.bed_size_x_mm}x{self.bed_size_y_mm}x{self.bed_size_z_mm}"
        return None


class PrinterSummary(BaseModel):
    """Lightweight printer summary for embedding in responses and dropdowns."""

    id: UUID
    name: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class PrinterListResponse(BaseModel):
    """Schema for paginated printer list."""

    printers: list[PrinterResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
