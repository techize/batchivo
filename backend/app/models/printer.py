"""Printer model for 3D printers available for production runs."""

import uuid
from typing import TYPE_CHECKING, Any, Optional

from decimal import Decimal
from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.ams_slot_mapping import AMSSlotMapping
    from app.models.model_printer_config import ModelPrinterConfig
    from app.models.print_job import PrintJob
    from app.models.printer_connection import PrinterConnection
    from app.models.production_run import ProductionRun
    from app.models.production_run_plate import ProductionRunPlate
    from app.models.tenant import Tenant


class Printer(Base, UUIDMixin, TimestampMixin):
    """
    Printer represents a 3D printer available for production runs.

    Each printer can have different capabilities (bed size, materials, AMS)
    and different configurations for each model (prints per plate, times).

    Multi-tenant: Each printer belongs to a single tenant.
    """

    __tablename__ = "printers"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Printer Identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Printer name (e.g., 'Bambu A1 Mini')",
    )

    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Manufacturer name",
    )

    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Model name",
    )

    # Bed Size
    bed_size_x_mm: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Bed size X in millimeters",
    )

    bed_size_y_mm: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Bed size Y in millimeters",
    )

    bed_size_z_mm: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Bed size Z in millimeters",
    )

    # Printer Settings
    nozzle_diameter_mm: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        default=Decimal("0.4"),
        server_default="0.4",
        comment="Nozzle diameter in millimeters",
    )

    default_bed_temp: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Default bed temperature",
    )

    default_nozzle_temp: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Default nozzle temperature",
    )

    # Capabilities (JSON for flexibility)
    capabilities: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        server_default="{}",
        comment="Printer capabilities (AMS, materials, etc.)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether printer is active",
    )

    # Queue management status
    current_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="offline",
        server_default="offline",
        comment="Current operational status for queue management (idle, printing, error, offline)",
    )

    current_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("print_jobs.id", ondelete="SET NULL"),
        nullable=True,
        comment="Currently printing job (if any)",
    )

    # Current job relationship (for queue management)
    current_job: Mapped[Optional["PrintJob"]] = relationship(
        "PrintJob",
        foreign_keys=[current_job_id],
        lazy="selectin",
        post_update=True,  # Avoid circular dependency issues
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="printers",
        lazy="select",
    )

    model_printer_configs: Mapped[list["ModelPrinterConfig"]] = relationship(
        "ModelPrinterConfig",
        back_populates="printer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    production_runs: Mapped[list["ProductionRun"]] = relationship(
        "ProductionRun",
        back_populates="printer",
        lazy="select",
    )

    production_run_plates: Mapped[list["ProductionRunPlate"]] = relationship(
        "ProductionRunPlate",
        back_populates="printer",
        lazy="select",
    )

    # Bambu integration relationships
    connection: Mapped[Optional["PrinterConnection"]] = relationship(
        "PrinterConnection",
        back_populates="printer",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )

    ams_slot_mappings: Mapped[list["AMSSlotMapping"]] = relationship(
        "AMSSlotMapping",
        back_populates="printer",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Print queue jobs assigned to this printer
    print_jobs: Mapped[list["PrintJob"]] = relationship(
        "PrintJob",
        back_populates="assigned_printer",
        foreign_keys="[PrintJob.assigned_printer_id]",
        lazy="select",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_printer_tenant_name"),
        {"comment": "3D printers available for production runs"},
    )

    @property
    def bed_size_str(self) -> Optional[str]:
        """Return bed size as formatted string (e.g., '180x180x180')."""
        if self.bed_size_x_mm and self.bed_size_y_mm and self.bed_size_z_mm:
            return f"{self.bed_size_x_mm}x{self.bed_size_y_mm}x{self.bed_size_z_mm}"
        return None

    def __repr__(self) -> str:
        return f"<Printer(name={self.name}, manufacturer={self.manufacturer})>"
