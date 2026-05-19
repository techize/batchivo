"""FilamentType shared definition model."""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class FilamentType(Base, UUIDMixin, TimestampMixin):
    """
    Shared filament type definition (brand + colour + material combination).

    Represents a distinct filament product that multiple physical spools can
    reference. Acts as the deduplication key for brand + color + material_type_id
    per tenant (DATA-04).
    """

    __tablename__ = "filament_types"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Material type FK
    material_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material_types.id"),
        nullable=False,
        index=True,
        comment="Material type (PLA, PETG, etc.)",
    )

    # Deduplication key fields (DATA-04) — NOT NULL
    brand: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Filament brand/manufacturer",
    )

    color: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Filament colour name",
    )

    # Optional colour / appearance metadata
    color_hex: Mapped[Optional[str]] = mapped_column(
        String(9),
        nullable=True,
        comment="Hex colour code (RGB or RGBA format, e.g., FF5733 or 00FF5733)",
    )

    finish: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Finish type (matte, glossy, metallic, etc.)",
    )

    pattern: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Pattern type (marble, gradient, speckled, etc.)",
    )

    spool_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Spool type (cardboard, plastic, refill, etc.)",
    )

    # Filament specifications
    diameter: Mapped[float] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        default=1.75,
        server_default="1.75",
        comment="Filament diameter in mm (typically 1.75 or 2.85)",
    )

    density: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 3),
        nullable=True,
        comment="Filament density in g/cm³ (e.g., 1.24 for PLA)",
    )

    # Recommended print temperatures
    extruder_temp: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Recommended extruder temperature in °C",
    )

    bed_temp: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Recommended bed temperature in °C",
    )

    # Special filament properties
    translucent: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether filament is translucent/transparent",
    )

    glow: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether filament is glow-in-the-dark",
    )

    # Sample tracking (DATA-04)
    has_sample: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether a display benchy has been printed for this filament type",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes about this filament type",
    )

    # Relationships
    material_type: Mapped["MaterialType"] = relationship(
        "MaterialType",
        lazy="joined",
    )

    spools: Mapped[list["Spool"]] = relationship(
        "Spool",
        back_populates="filament_type",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<FilamentType(brand={self.brand!r}, color={self.color!r})>"
