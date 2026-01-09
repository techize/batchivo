"""ModelComponent model for non-material costs (magnets, inserts, etc.)."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.consumable import ConsumableType
    from app.models.model import Model


class ModelComponent(Base, UUIDMixin, TimestampMixin):
    """
    Non-material component costs for models.

    Tracks additional components used in models like magnets, heat inserts,
    screws, glue, paint, etc. Each component has a quantity and unit cost.

    Can optionally link to a ConsumableType for automatic cost tracking
    and inventory management.
    """

    __tablename__ = "model_components"

    # Reference
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Model this component belongs to",
    )

    # Optional link to consumable inventory
    consumable_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("consumable_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Link to consumable type for automatic cost/inventory tracking",
    )

    # Component Info
    component_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Component name (e.g., 'M3 x 10mm magnet', 'M3 heat insert')",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Quantity of this component used in model",
    )

    unit_cost: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Cost per unit in local currency",
    )

    supplier: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Supplier/vendor name",
    )

    # Relationships
    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="components",
    )

    consumable_type: Mapped[Optional["ConsumableType"]] = relationship(
        "ConsumableType",
        back_populates="model_components",
    )

    def __repr__(self) -> str:
        return f"<ModelComponent(name={self.component_name}, qty={self.quantity}, unit_cost={self.unit_cost})>"

    @property
    def total_cost(self) -> float:
        """Calculate total cost for this component."""
        return self.quantity * float(self.unit_cost)

    @property
    def effective_unit_cost(self) -> float:
        """Get unit cost from linked consumable or manual entry."""
        if self.consumable_type and self.consumable_type.current_cost_per_unit:
            return float(self.consumable_type.current_cost_per_unit)
        return float(self.unit_cost)
