"""SpoolmanDB reference data models.

These tables store data synced from the SpoolmanDB community database.
https://github.com/Donkie/SpoolmanDB

Data is read-only and refreshed periodically via sync service.
"""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class SpoolmanDBManufacturer(Base, UUIDMixin, TimestampMixin):
    """
    Manufacturer/brand information from SpoolmanDB.

    Examples: Bambu Lab, Polymaker, Prusament, eSun, etc.
    """

    __tablename__ = "spoolmandb_manufacturers"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Manufacturer name (e.g., Bambu Lab, Polymaker)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this manufacturer is still in SpoolmanDB",
    )

    # Relationship to filaments
    filaments: Mapped[list["SpoolmanDBFilament"]] = relationship(
        back_populates="manufacturer",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<SpoolmanDBManufacturer(name='{self.name}')>"


class SpoolmanDBFilament(Base, UUIDMixin, TimestampMixin):
    """
    Filament product information from SpoolmanDB.

    Each record represents a specific filament variant:
    manufacturer + material + colour + weight + diameter combination.
    """

    __tablename__ = "spoolmandb_filaments"

    # SpoolmanDB's unique identifier for this filament
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="SpoolmanDB unique identifier",
    )

    # Manufacturer relationship
    manufacturer_id: Mapped[str] = mapped_column(
        ForeignKey("spoolmandb_manufacturers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    manufacturer: Mapped[SpoolmanDBManufacturer] = relationship(
        back_populates="filaments",
    )

    # Product identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Product/colour name (e.g., Galaxy Black, Jade White)",
    )

    material: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Material type code (e.g., PLA, PETG, ABS, TPU)",
    )

    # Physical properties
    density: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Material density in g/cm³",
    )

    diameter: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Filament diameter in mm (1.75 or 2.85)",
    )

    weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Net filament weight in grams",
    )

    spool_weight: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Empty spool weight in grams",
    )

    spool_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Spool material type (e.g., plastic, cardboard)",
    )

    # Colour information
    color_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Colour name",
    )

    color_hex: Mapped[str | None] = mapped_column(
        String(9),
        nullable=True,
        comment="Colour hex code (RGB: FF5733 or RGBA: 00FFFFFF)",
    )

    # Temperature settings
    extruder_temp: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Recommended extruder temperature (°C)",
    )

    bed_temp: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Recommended bed temperature (°C)",
    )

    # Visual/material characteristics
    finish: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Surface finish (e.g., matte, glossy)",
    )

    translucent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether filament is translucent",
    )

    glow: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether filament glows in the dark",
    )

    pattern: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Pattern type (e.g., marble, sparkle)",
    )

    multi_color_direction: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Multi-colour direction (coaxial, longitudinal)",
    )

    # Additional hex colours for multi-colour filaments
    color_hexes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated hex codes for multi-colour filaments",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this filament is still in SpoolmanDB",
    )

    def __repr__(self) -> str:
        return f"<SpoolmanDBFilament(name='{self.name}', material='{self.material}')>"
