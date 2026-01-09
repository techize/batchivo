"""Spool model for filament inventory tracking."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Spool(Base, UUIDMixin, TimestampMixin):
    """
    Filament spool inventory item.

    Tracks individual spools of 3D printing filament with purchase info,
    weight tracking, and material type.
    """

    __tablename__ = "spools"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Material type (reference data)
    material_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material_types.id"),
        nullable=False,
        index=True,
        comment="Material type (PLA, PETG, etc.)",
    )

    # Basic Info
    spool_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="User-friendly spool ID (e.g., FIL-001, PLA-RED-001)",
    )

    brand: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Filament brand/manufacturer",
    )

    color: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Filament color",
    )

    color_hex: Mapped[Optional[str]] = mapped_column(
        String(9),
        nullable=True,
        comment="Hex color code (RGB or RGBA format, e.g., FF5733 or 00FF5733)",
    )

    finish: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Finish type (matte, glossy, metallic, etc.)",
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

    # Recommended print temperatures (per-filament override of material defaults)
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

    # Weight Tracking (in grams)
    initial_weight: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Initial filament weight in grams (e.g., 1000.00 for 1kg)",
    )

    current_weight: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Current filament weight in grams",
    )

    empty_spool_weight: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Weight of empty spool in grams (for gross weight calculations)",
    )

    # Purchase Information
    purchase_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date spool was purchased",
    )

    purchase_price: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Purchase price in local currency",
    )

    supplier: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Supplier/vendor name",
    )

    # Batch Tracking
    purchased_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of spools purchased in this batch",
    )

    spools_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of spools remaining from this batch",
    )

    # Storage & Organization
    storage_location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Physical storage location (e.g., Shelf A, Box 3)",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes about this spool",
    )

    # QR Code Integration
    qr_code_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="QR code identifier for quick scanning",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether spool is active (not empty/discarded)",
    )

    # Relationships
    material_type: Mapped["MaterialType"] = relationship(
        "MaterialType",
        lazy="joined",
    )

    production_run_materials: Mapped[list["ProductionRunMaterial"]] = relationship(
        "ProductionRunMaterial",
        back_populates="spool",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Spool(id={self.spool_id}, material={self.material_type.code if self.material_type else 'N/A'}, color={self.color})>"

    @property
    def remaining_weight(self) -> float:
        """Calculate remaining filament weight."""
        return float(self.current_weight)

    @property
    def remaining_percentage(self) -> float:
        """Calculate remaining filament as percentage."""
        if self.initial_weight <= 0:
            return 0.0
        return (float(self.current_weight) / float(self.initial_weight)) * 100

    @property
    def cost_per_gram(self) -> Optional[float]:
        """Calculate cost per gram from purchase price and initial weight."""
        if self.purchase_price is not None and self.initial_weight > 0:
            return float(self.purchase_price) / float(self.initial_weight)
        return None

    @property
    def is_low_stock(self, threshold: float = 20.0) -> bool:
        """Check if spool is below threshold percentage."""
        return self.remaining_percentage < threshold
