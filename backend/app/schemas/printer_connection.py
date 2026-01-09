"""Pydantic schemas for PrinterConnection API."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConnectionType(str, Enum):
    """Supported printer connection types."""

    BAMBU_LAN = "bambu_lan"
    BAMBU_CLOUD = "bambu_cloud"
    OCTOPRINT = "octoprint"
    KLIPPER = "klipper"
    MANUAL = "manual"


class PrinterConnectionBase(BaseModel):
    """Base printer connection schema with common fields."""

    connection_type: ConnectionType = Field(
        default=ConnectionType.MANUAL,
        description="Type of printer connection",
    )

    serial_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Bambu printer serial number (found on printer screen)",
    )

    ip_address: Optional[str] = Field(
        None,
        max_length=45,
        description="Printer IP address for LAN connections",
    )

    port: int = Field(
        default=8883,
        ge=1,
        le=65535,
        description="Connection port (default 8883 for Bambu MQTT)",
    )

    access_code: Optional[str] = Field(
        None,
        max_length=100,
        description="LAN access code from Bambu printer settings",
    )

    cloud_username: Optional[str] = Field(
        None,
        max_length=100,
        description="Cloud account username for cloud connections",
    )

    cloud_token: Optional[str] = Field(
        None,
        description="Cloud access token for cloud connections",
    )

    ams_count: int = Field(
        default=0,
        ge=0,
        le=4,
        description="Number of AMS units connected (0-4)",
    )

    is_enabled: bool = Field(
        default=True,
        description="Whether connection is enabled",
    )

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Basic IP address validation."""
        if v is None:
            return v
        # Simple validation - more thorough validation can be added
        parts = v.split(".")
        if len(parts) == 4:
            try:
                for part in parts:
                    num = int(part)
                    if not 0 <= num <= 255:
                        raise ValueError("Invalid IP address octet")
                return v
            except ValueError:
                pass
        # Could be IPv6 or hostname, allow it
        return v


class PrinterConnectionCreate(PrinterConnectionBase):
    """Schema for creating a new printer connection."""

    pass


class PrinterConnectionUpdate(BaseModel):
    """Schema for updating a printer connection (all fields optional)."""

    connection_type: Optional[ConnectionType] = None
    serial_number: Optional[str] = Field(None, max_length=50)
    ip_address: Optional[str] = Field(None, max_length=45)
    port: Optional[int] = Field(None, ge=1, le=65535)
    access_code: Optional[str] = Field(None, max_length=100)
    cloud_username: Optional[str] = Field(None, max_length=100)
    cloud_token: Optional[str] = None
    ams_count: Optional[int] = Field(None, ge=0, le=4)
    is_enabled: Optional[bool] = None


class PrinterConnectionResponse(PrinterConnectionBase):
    """Schema for printer connection responses."""

    id: UUID
    tenant_id: UUID
    printer_id: UUID

    # Runtime status
    is_connected: bool = False
    last_connected_at: Optional[datetime] = None
    last_status_at: Optional[datetime] = None
    connection_error: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    # Don't expose sensitive tokens in responses
    @field_validator("access_code", mode="before")
    @classmethod
    def mask_access_code(cls, v: Optional[str]) -> Optional[str]:
        """Mask access code in responses."""
        if v:
            return "****" + v[-4:] if len(v) > 4 else "****"
        return None

    @field_validator("cloud_token", mode="before")
    @classmethod
    def mask_cloud_token(cls, v: Optional[str]) -> Optional[str]:
        """Mask cloud token in responses."""
        if v:
            return "****"
        return None


class PrinterConnectionStatus(BaseModel):
    """Schema for printer connection status."""

    printer_id: UUID
    connection_type: ConnectionType
    is_enabled: bool
    is_connected: bool
    last_connected_at: Optional[datetime] = None
    last_status_at: Optional[datetime] = None
    connection_error: Optional[str] = None
    ams_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BambuPrinterStatus(BaseModel):
    """Schema for Bambu printer live status from MQTT."""

    serial_number: str
    is_online: bool = False

    # Print progress
    print_status: Optional[str] = None  # RUNNING, PAUSED, IDLE, etc.
    print_percentage: Optional[int] = None
    current_layer: Optional[int] = None
    total_layers: Optional[int] = None
    remaining_time_minutes: Optional[int] = None
    current_file: Optional[str] = None

    # Temperatures
    nozzle_temp: Optional[float] = None
    nozzle_target_temp: Optional[float] = None
    bed_temp: Optional[float] = None
    bed_target_temp: Optional[float] = None
    chamber_temp: Optional[float] = None

    # Error info
    error_code: Optional[int] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
