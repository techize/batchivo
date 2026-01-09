"""PrinterConnection model for printer integration connections (Bambu, OctoPrint, etc.)."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.printer import Printer
    from app.models.tenant import Tenant


class ConnectionType(str, Enum):
    """Supported printer connection types."""

    BAMBU_LAN = "bambu_lan"  # Direct LAN MQTT connection
    BAMBU_CLOUD = "bambu_cloud"  # Cloud MQTT connection
    OCTOPRINT = "octoprint"  # OctoPrint REST API
    KLIPPER = "klipper"  # Klipper/Moonraker API
    MANUAL = "manual"  # Manual tracking (no auto-sync)


class PrinterConnection(Base, UUIDMixin, TimestampMixin):
    """
    PrinterConnection stores connection details for printer integrations.

    Supports multiple connection types:
    - Bambu Lab (LAN MQTT or Cloud MQTT)
    - OctoPrint (REST API)
    - Klipper/Moonraker (REST API)

    Each printer can have one active connection configuration.
    Sensitive data (access codes, tokens) should be encrypted at rest.

    Multi-tenant: Each connection belongs to a single tenant.
    """

    __tablename__ = "printer_connections"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Link to printer
    printer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("printers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated printer ID",
    )

    # Connection type
    connection_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ConnectionType.MANUAL.value,
        comment="Connection type (bambu_lan, bambu_cloud, octoprint, klipper, manual)",
    )

    # Bambu-specific fields
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Bambu printer serial number (from printer screen)",
    )

    # Network connection details
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        comment="Printer IP address (for LAN connections)",
    )

    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=8883,
        server_default="8883",
        comment="Connection port (default 8883 for Bambu MQTT)",
    )

    # Authentication (sensitive - consider encryption)
    access_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="LAN access code (from Bambu printer settings)",
    )

    # Cloud connection fields
    cloud_username: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Cloud account username/user_id (for cloud connections)",
    )

    cloud_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Cloud access token (for cloud connections)",
    )

    # AMS Configuration
    ams_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of AMS units connected (0-4)",
    )

    # Connection status (runtime state)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether connection is enabled",
    )

    is_connected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Current connection status (runtime)",
    )

    last_connected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful connection timestamp",
    )

    last_status_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last status message received timestamp",
    )

    connection_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Last connection error message",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        lazy="select",
    )

    printer: Mapped["Printer"] = relationship(
        "Printer",
        back_populates="connection",
        lazy="joined",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("printer_id", name="uq_printer_connection_printer"),
        {"comment": "Printer connection configurations for integrations"},
    )

    def __repr__(self) -> str:
        return f"<PrinterConnection(printer_id={self.printer_id}, type={self.connection_type})>"

    @property
    def is_bambu(self) -> bool:
        """Check if this is a Bambu Lab connection."""
        return self.connection_type in (
            ConnectionType.BAMBU_LAN.value,
            ConnectionType.BAMBU_CLOUD.value,
        )

    @property
    def mqtt_topic_prefix(self) -> Optional[str]:
        """Get MQTT topic prefix for this connection."""
        if self.is_bambu and self.serial_number:
            return f"device/{self.serial_number}"
        return None

    @property
    def total_ams_slots(self) -> int:
        """Calculate total AMS slots (4 per unit)."""
        return self.ams_count * 4
