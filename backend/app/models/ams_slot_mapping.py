"""AMSSlotMapping model for mapping Bambu AMS slots to Batchivo spools."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.printer import Printer
    from app.models.spool import Spool
    from app.models.tenant import Tenant


class AMSSlotMapping(Base, UUIDMixin, TimestampMixin):
    """
    AMSSlotMapping maps Bambu Lab AMS slots to Batchivo spool inventory.

    Each AMS unit has 4 trays (slots), identified by:
    - ams_id: 0-3 (which AMS unit in a daisy-chain)
    - tray_id: 0-3 (which slot within the AMS unit)

    The absolute slot number formula: (ams_id * 4) + tray_id

    Users can manually map slots to spools, or the system can
    auto-map based on RFID tag UID matching.

    Multi-tenant: Each mapping belongs to a single tenant.
    """

    __tablename__ = "ams_slot_mappings"

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

    # AMS slot identification
    ams_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="AMS unit index (0-3 for up to 4 daisy-chained units)",
    )

    tray_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Tray/slot index within AMS unit (0-3)",
    )

    # Mapped spool (nullable - slot may be empty or unmapped)
    spool_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("spools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Mapped Batchivo spool ID (null if unmapped)",
    )

    # RFID tracking (for Bambu Lab filament auto-detection)
    rfid_tag_uid: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
        comment="RFID tag UID from AMS (for Bambu filament)",
    )

    # Last reported status from AMS (cached for UI display)
    last_reported_type: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Last reported filament type from AMS (e.g., PLA, PETG)",
    )

    last_reported_color: Mapped[Optional[str]] = mapped_column(
        String(9),
        nullable=True,
        comment="Last reported color from AMS (RRGGBBAA hex)",
    )

    last_reported_remain: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Last reported remaining percentage from AMS (0-100)",
    )

    last_reported_temp_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Last reported min nozzle temp from AMS",
    )

    last_reported_temp_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Last reported max nozzle temp from AMS",
    )

    # Mapping metadata
    is_auto_mapped: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether mapping was auto-created via RFID match",
    )

    has_filament: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether AMS reports filament in this slot",
    )

    is_bambu_filament: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether filament has valid Bambu RFID tag",
    )

    # Sync timestamps
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time spool was synced from AMS data",
    )

    last_status_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time AMS status was received for this slot",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        lazy="select",
    )

    printer: Mapped["Printer"] = relationship(
        "Printer",
        back_populates="ams_slot_mappings",
        lazy="select",
    )

    spool: Mapped[Optional["Spool"]] = relationship(
        "Spool",
        lazy="joined",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("printer_id", "ams_id", "tray_id", name="uq_ams_slot_printer_ams_tray"),
        {"comment": "AMS slot to spool mappings for Bambu printers"},
    )

    def __repr__(self) -> str:
        return f"<AMSSlotMapping(printer={self.printer_id}, ams={self.ams_id}, tray={self.tray_id}, spool={self.spool_id})>"

    @property
    def absolute_slot_id(self) -> int:
        """Calculate absolute slot ID across all AMS units."""
        return (self.ams_id * 4) + self.tray_id

    @property
    def slot_display_name(self) -> str:
        """Human-readable slot name (e.g., 'AMS 1 Slot 2')."""
        return f"AMS {self.ams_id + 1} Slot {self.tray_id + 1}"

    @property
    def color_hex_normalized(self) -> Optional[str]:
        """Return color as 6-char hex (RGB without alpha)."""
        if self.last_reported_color and len(self.last_reported_color) >= 6:
            return self.last_reported_color[:6]
        return None
