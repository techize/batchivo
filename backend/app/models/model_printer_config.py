"""ModelPrinterConfig model for printer-specific configuration of models."""

import uuid
from typing import TYPE_CHECKING, Optional, Any

from decimal import Decimal
from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    Text,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.printer import Printer


class ModelPrinterConfig(Base, UUIDMixin, TimestampMixin):
    """
    ModelPrinterConfig stores printer-specific settings for each model.

    Different printers can print different quantities per plate, have different
    print times, and require different slicer settings. This table captures
    those differences.

    Relationship: Each Model can have multiple configs (one per Printer).
    Unique constraint: Only one config per (model_id, printer_id) pair.

    If no config exists for a model/printer combination, the system falls back
    to the Model's default values (prints_per_plate, print_time_minutes, etc.).
    """

    __tablename__ = "model_printer_configs"

    # Foreign Keys
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Model this config applies to",
    )

    printer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("printers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Printer this config is for",
    )

    # Print Settings
    prints_per_plate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="How many of this model fit on one plate for this printer",
    )

    print_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total print time for full plate (all prints_per_plate items)",
    )

    material_weight_grams: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Material weight for ONE item (not full plate)",
    )

    # Temperature Settings
    bed_temperature: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Bed temperature for this model on this printer",
    )

    nozzle_temperature: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Nozzle temperature for this model on this printer",
    )

    # Slicer Settings
    layer_height: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Layer height in millimeters",
    )

    infill_percentage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Infill percentage (0-100)",
    )

    supports: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default="false",
        comment="Whether supports are required",
    )

    brim: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        server_default="false",
        comment="Whether brim is required",
    )

    # Additional slicer settings (JSON for flexibility)
    slicer_settings: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        server_default="{}",
        comment="Additional slicer settings (speed, retraction, etc.)",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="printer_configs",
        lazy="selectin",
    )

    printer: Mapped["Printer"] = relationship(
        "Printer",
        back_populates="model_printer_configs",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("model_id", "printer_id", name="uq_model_printer"),
        CheckConstraint("prints_per_plate > 0", name="check_prints_per_plate_positive"),
        {
            "comment": "Printer-specific configuration for each model (prints per plate, times, settings)"
        },
    )

    @property
    def print_time_per_item_minutes(self) -> Optional[int]:
        """Calculate print time per individual item."""
        if self.print_time_minutes and self.prints_per_plate:
            return self.print_time_minutes // self.prints_per_plate
        return None

    @property
    def material_weight_per_plate_grams(self) -> Optional[Decimal]:
        """Calculate total material weight for a full plate."""
        if self.material_weight_grams and self.prints_per_plate:
            return self.material_weight_grams * self.prints_per_plate
        return None

    def __repr__(self) -> str:
        return f"<ModelPrinterConfig(model_id={self.model_id}, printer_id={self.printer_id}, prints_per_plate={self.prints_per_plate})>"
