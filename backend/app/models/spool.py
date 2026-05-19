"""Spool model for filament inventory tracking."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Spool(Base, UUIDMixin, TimestampMixin):
    """
    Filament spool inventory item.

    Tracks individual physical spools of 3D printing filament with purchase info,
    weight tracking, and a reference to the FilamentType that defines the filament
    specifications.
    """

    __tablename__ = "spools"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # FilamentType reference (two-tier model: type definition + per-unit spool)
    filament_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("filament_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FilamentType this spool belongs to",
    )

    # Basic Info
    spool_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="User-friendly spool ID (e.g., FIL-001, PLA-RED-001)",
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

    # Storage & Organization
    storage_location: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Physical storage location (e.g., Shelf A, Box 3)",
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

    is_labeled: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether a physical label has been printed for this spool",
    )

    # Relationships
    filament_type: Mapped["FilamentType"] = relationship(
        "FilamentType",
        lazy="joined",
    )

    production_run_materials: Mapped[list["ProductionRunMaterial"]] = relationship(
        "ProductionRunMaterial",
        back_populates="spool",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Spool(id={self.spool_id}, filament_type_id={self.filament_type_id})>"

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
