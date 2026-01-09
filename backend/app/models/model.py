"""Model for 3D printed items (individual printed parts)."""

import uuid
from typing import TYPE_CHECKING, Optional

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model_component import ModelComponent
    from app.models.model_file import ModelFile
    from app.models.model_material import ModelMaterial
    from app.models.model_printer_config import ModelPrinterConfig
    from app.models.print_job import PrintJob
    from app.models.production_run_plate import ProductionRunPlate


class Model(Base, UUIDMixin, TimestampMixin):
    """
    Model represents a 3D printed item (individual printed part).

    This is what was previously called "Product" - the actual printed item
    with materials (BOM), components, labor, and cost tracking.

    Multiple Models can be combined into a sellable Product.
    """

    __tablename__ = "models"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Model Identification
    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Stock Keeping Unit (unique per tenant)",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Model name",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Model description/notes",
    )

    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Model category (e.g., 'Miniatures', 'Functional Parts')",
    )

    # Media
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Model image URL",
    )

    # Labor Costing
    labor_hours: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
        comment="Labor hours required (post-processing, assembly, etc.)",
    )

    labor_rate_override: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Override labor rate for this model (£/hour). If null, use tenant default.",
    )

    # Overhead
    overhead_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        server_default="0",
        comment="Overhead percentage to apply (0-100). If 0, use tenant default.",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether model is active",
    )

    # Model Metadata
    designer: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Model designer name (e.g., 'CinderWings')",
    )

    source: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Model source platform (e.g., 'Thangs', 'Patreon')",
    )

    print_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Print time in minutes (for full plate if prints_per_plate > 1)",
    )

    prints_per_plate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of items printed per plate (for batch printing). Material weights and print time are divided by this.",
    )

    machine: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Printer/machine used (e.g., 'Bambulabs A1 Mini')",
    )

    last_printed_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this model was printed",
    )

    units_in_stock: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        server_default="0",
        comment="Number of printed units in inventory",
    )

    # Relationships
    materials: Mapped[list["ModelMaterial"]] = relationship(
        "ModelMaterial",
        back_populates="model",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    components: Mapped[list["ModelComponent"]] = relationship(
        "ModelComponent",
        back_populates="model",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    production_run_items: Mapped[list["ProductionRunItem"]] = relationship(
        "ProductionRunItem",
        back_populates="model",
        lazy="select",
    )

    product_models: Mapped[list["ProductModel"]] = relationship(
        "ProductModel",
        back_populates="model",
        lazy="select",
    )

    # Printer-specific configurations
    printer_configs: Mapped[list["ModelPrinterConfig"]] = relationship(
        "ModelPrinterConfig",
        back_populates="model",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Multi-plate run plates
    production_run_plates: Mapped[list["ProductionRunPlate"]] = relationship(
        "ProductionRunPlate",
        back_populates="model",
        lazy="select",
    )

    # Print queue jobs
    print_jobs: Mapped[list["PrintJob"]] = relationship(
        "PrintJob",
        back_populates="model",
        lazy="select",
    )

    # 3D model files (STL, 3MF, gcode, etc.)
    files: Mapped[list["ModelFile"]] = relationship(
        "ModelFile",
        back_populates="model",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_model_tenant_sku"),
        {"comment": "3D printed model/part with Bill of Materials and cost tracking"},
    )

    def __repr__(self) -> str:
        return f"<Model(sku={self.sku}, name={self.name})>"
