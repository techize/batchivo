"""Pydantic schemas for AMS Slot Mapping API."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class AMSSlotMappingBase(BaseModel):
    """Base AMS slot mapping schema."""

    ams_id: int = Field(
        ...,
        ge=0,
        le=3,
        description="AMS unit index (0-3 for up to 4 daisy-chained units)",
    )

    tray_id: int = Field(
        ...,
        ge=0,
        le=3,
        description="Tray/slot index within AMS unit (0-3)",
    )

    spool_id: Optional[UUID] = Field(
        None,
        description="Mapped Nozzly spool ID (null if unmapped)",
    )


class AMSSlotMappingCreate(AMSSlotMappingBase):
    """Schema for creating/updating an AMS slot mapping."""

    pass


class AMSSlotMappingUpdate(BaseModel):
    """Schema for updating an AMS slot mapping (all fields optional)."""

    spool_id: Optional[UUID] = None


class AMSSlotMappingResponse(BaseModel):
    """Schema for AMS slot mapping responses."""

    id: UUID
    tenant_id: UUID
    printer_id: UUID

    ams_id: int
    tray_id: int
    spool_id: Optional[UUID] = None

    # RFID data
    rfid_tag_uid: Optional[str] = None

    # Last reported status from AMS
    last_reported_type: Optional[str] = None
    last_reported_color: Optional[str] = None
    last_reported_remain: Optional[int] = None
    last_reported_temp_min: Optional[int] = None
    last_reported_temp_max: Optional[int] = None

    # Flags
    is_auto_mapped: bool = False
    has_filament: bool = False
    is_bambu_filament: bool = False

    # Timestamps
    last_synced_at: Optional[datetime] = None
    last_status_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def absolute_slot_id(self) -> int:
        """Calculate absolute slot ID across all AMS units."""
        return (self.ams_id * 4) + self.tray_id

    @computed_field
    @property
    def slot_display_name(self) -> str:
        """Human-readable slot name (e.g., 'AMS 1 Slot 2')."""
        return f"AMS {self.ams_id + 1} Slot {self.tray_id + 1}"

    @computed_field
    @property
    def color_hex_normalized(self) -> Optional[str]:
        """Return color as 6-char hex (RGB without alpha)."""
        if self.last_reported_color and len(self.last_reported_color) >= 6:
            return self.last_reported_color[:6]
        return None


class AMSSlotMappingWithSpool(AMSSlotMappingResponse):
    """AMS slot mapping response with embedded spool summary."""

    spool_summary: Optional["SpoolSummaryForAMS"] = None

    model_config = ConfigDict(from_attributes=True)


class SpoolSummaryForAMS(BaseModel):
    """Lightweight spool summary for AMS slot display."""

    id: UUID
    spool_id: str
    brand: str
    color: str
    color_hex: Optional[str] = None
    material_type_code: Optional[str] = None
    current_weight: float
    initial_weight: float

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def remaining_percentage(self) -> float:
        """Calculate remaining percentage."""
        if self.initial_weight <= 0:
            return 0.0
        return (self.current_weight / self.initial_weight) * 100


class AMSStatusFromMQTT(BaseModel):
    """Schema for parsing AMS status from Bambu MQTT messages."""

    ams_id: int
    humidity: Optional[float] = None
    temperature: Optional[float] = None
    trays: list["AMSTrayStatus"]


class AMSTrayStatus(BaseModel):
    """Schema for individual AMS tray status from MQTT."""

    tray_id: int
    tag_uid: Optional[str] = None
    tray_type: Optional[str] = None
    tray_color: Optional[str] = None  # RRGGBBAA hex
    tray_weight: Optional[int] = None  # Initial weight in grams
    tray_diameter: Optional[float] = None
    nozzle_temp_min: Optional[int] = None
    nozzle_temp_max: Optional[int] = None
    bed_temp: Optional[int] = None
    remain: Optional[int] = None  # Remaining percentage 0-100
    tray_info_idx: Optional[str] = None  # Bambu filament code
    tray_sub_brands: Optional[str] = None


class AMSFullStatus(BaseModel):
    """Schema for full AMS status response."""

    printer_id: UUID
    ams_units: list[AMSStatusFromMQTT]
    tray_now: Optional[int] = None  # Currently active tray (absolute ID)
    last_updated_at: Optional[datetime] = None


class AMSSlotBulkMapRequest(BaseModel):
    """Schema for bulk mapping AMS slots to spools."""

    mappings: list["AMSSlotMappingCreate"]


class AMSSlotListResponse(BaseModel):
    """Schema for listing all AMS slots for a printer."""

    printer_id: UUID
    ams_count: int
    total_slots: int
    slots: list[AMSSlotMappingWithSpool]

    model_config = ConfigDict(from_attributes=True)


# Update forward references
AMSSlotMappingWithSpool.model_rebuild()
AMSStatusFromMQTT.model_rebuild()
