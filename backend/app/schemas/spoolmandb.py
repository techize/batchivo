"""Pydantic schemas for SpoolmanDB data."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SpoolmanDBManufacturerBase(BaseModel):
    """Base schema for manufacturer."""

    name: str


class SpoolmanDBManufacturerResponse(SpoolmanDBManufacturerBase):
    """Response schema for manufacturer."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SpoolmanDBManufacturerWithCount(SpoolmanDBManufacturerResponse):
    """Manufacturer with filament count."""

    filament_count: int = 0


class SpoolmanDBFilamentBase(BaseModel):
    """Base schema for filament."""

    external_id: str
    name: str
    material: str
    density: float | None = None
    diameter: float
    weight: int
    spool_weight: int | None = None
    spool_type: str | None = None
    color_name: str | None = None
    color_hex: str | None = None
    extruder_temp: int | None = None
    bed_temp: int | None = None
    finish: str | None = None
    translucent: bool = False
    glow: bool = False
    pattern: str | None = None
    multi_color_direction: str | None = None
    color_hexes: str | None = None


class SpoolmanDBFilamentResponse(SpoolmanDBFilamentBase):
    """Response schema for filament."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    manufacturer_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SpoolmanDBFilamentWithManufacturer(SpoolmanDBFilamentResponse):
    """Filament with manufacturer details."""

    manufacturer_name: str


class SpoolmanDBFilamentListResponse(BaseModel):
    """Paginated list of filaments."""

    filaments: list[SpoolmanDBFilamentWithManufacturer]
    total: int
    page: int
    page_size: int


class SpoolmanDBManufacturerListResponse(BaseModel):
    """List of manufacturers."""

    manufacturers: list[SpoolmanDBManufacturerWithCount]
    total: int


class SpoolmanDBSyncResponse(BaseModel):
    """Response from sync operation."""

    success: bool
    manufacturers_added: int
    manufacturers_updated: int
    filaments_added: int
    filaments_updated: int
    message: str


class SpoolmanDBStatsResponse(BaseModel):
    """Statistics about SpoolmanDB data."""

    total_manufacturers: int
    total_filaments: int
    materials: list[str]
    last_sync: datetime | None = None
