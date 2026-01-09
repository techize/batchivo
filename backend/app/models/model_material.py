"""ModelMaterial model for Bill of Materials (BOM) tracking."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.spool import Spool


class ModelMaterial(Base, UUIDMixin, TimestampMixin):
    """
    Bill of Materials (BOM) entry linking models to filament spools.

    Tracks which materials (spools) are used in a model and how much.
    Stores a snapshot of cost_per_gram at time of adding for historical accuracy.
    """

    __tablename__ = "model_materials"

    # References
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Model this material belongs to",
    )

    spool_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("spools.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Spool (material type/color/brand combination) used",
    )

    # Usage & Cost
    weight_grams: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Weight of this material used in model (grams)",
    )

    cost_per_gram: Mapped[float] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="Cost per gram at time of adding (snapshot for historical accuracy)",
    )

    # Relationships
    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="materials",
    )

    spool: Mapped["Spool"] = relationship(
        "Spool",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<ModelMaterial(model_id={self.model_id}, spool_id={self.spool_id}, weight={self.weight_grams}g)>"

    @property
    def total_cost(self) -> float:
        """Calculate total cost for this material in the model."""
        return float(self.weight_grams) * float(self.cost_per_gram)
