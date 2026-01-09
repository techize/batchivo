"""Consumable inventory models for tracking magnets, inserts, hardware, etc."""

import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.model_component import ModelComponent
    from app.models.production_run import ProductionRun
    from app.models.tenant import Tenant


class ConsumableType(Base, UUIDMixin, TimestampMixin):
    """
    Consumable type definition.

    Tracks types of consumables like magnets, heat inserts, screws, paint, etc.
    Each type has stock levels and purchasing information.
    """

    __tablename__ = "consumable_types"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant this consumable type belongs to",
    )

    # Identification
    sku: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unique SKU within tenant (e.g., MAG-3X1, INS-M3)",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Human-readable name (e.g., 'Magnet 3mm x 1mm')",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description",
    )

    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Category (magnets, inserts, hardware, finishing, packaging)",
    )

    # Unit information
    unit_of_measure: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="each",
        server_default="each",
        comment="Unit of measure (each, ml, g, pack)",
    )

    # Current pricing (updated from latest purchase)
    current_cost_per_unit: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="Current cost per unit from latest purchase",
    )

    # Stock management
    quantity_on_hand: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Current stock quantity",
    )

    reorder_point: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Stock level that triggers reorder alert",
    )

    reorder_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Suggested quantity to order when reordering",
    )

    # Supplier information
    preferred_supplier: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Preferred supplier/vendor name",
    )

    supplier_sku: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Supplier's SKU/product code",
    )

    supplier_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to purchase from supplier (e.g., Amazon product link)",
    )

    typical_lead_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Typical delivery time in days",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        nullable=False,
        comment="Whether this consumable type is active",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    purchases: Mapped[list["ConsumablePurchase"]] = relationship(
        "ConsumablePurchase",
        back_populates="consumable_type",
        cascade="all, delete-orphan",
    )
    usage_logs: Mapped[list["ConsumableUsage"]] = relationship(
        "ConsumableUsage",
        back_populates="consumable_type",
        cascade="all, delete-orphan",
    )
    model_components: Mapped[list["ModelComponent"]] = relationship(
        "ModelComponent",
        back_populates="consumable_type",
    )

    def __repr__(self) -> str:
        return f"<ConsumableType(sku={self.sku}, name={self.name}, qty={self.quantity_on_hand})>"

    @property
    def is_low_stock(self) -> bool:
        """Check if stock is below reorder point."""
        if self.reorder_point is None:
            return False
        return self.quantity_on_hand <= self.reorder_point

    @property
    def stock_value(self) -> float:
        """Calculate total value of stock on hand."""
        if self.current_cost_per_unit is None:
            return 0.0
        return self.quantity_on_hand * float(self.current_cost_per_unit)


class ConsumablePurchase(Base, UUIDMixin, TimestampMixin):
    """
    Consumable purchase records.

    Tracks batch purchases of consumables, enabling FIFO costing
    and purchase history.
    """

    __tablename__ = "consumable_purchases"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant this purchase belongs to",
    )

    # Reference
    consumable_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consumable_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Consumable type purchased",
    )

    # Purchase details
    quantity_purchased: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Quantity purchased",
    )

    total_cost: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total cost of purchase",
    )

    # Calculated field (stored for performance)
    cost_per_unit: Mapped[float] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        comment="Cost per unit (total_cost / quantity_purchased)",
    )

    # Source
    supplier: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Supplier/vendor name",
    )

    order_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Order number or reference",
    )

    purchase_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to purchase (e.g., Amazon product link)",
    )

    purchase_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date of purchase",
    )

    # FIFO tracking
    quantity_remaining: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Remaining quantity from this purchase (for FIFO costing)",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    consumable_type: Mapped["ConsumableType"] = relationship(
        "ConsumableType",
        back_populates="purchases",
    )

    def __repr__(self) -> str:
        return f"<ConsumablePurchase(qty={self.quantity_purchased}, cost={self.total_cost})>"


class ConsumableUsage(Base, UUIDMixin, TimestampMixin):
    """
    Consumable usage audit log.

    Records when consumables are used, linking to production runs
    or manual adjustments.
    """

    __tablename__ = "consumable_usage"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant this usage belongs to",
    )

    # Reference
    consumable_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("consumable_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Consumable type used",
    )

    # Optional links to what caused the usage
    production_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("production_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Production run that used this consumable",
    )

    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Model that used this consumable",
    )

    # Usage details
    quantity_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Quantity used (positive) or adjusted (negative for returns)",
    )

    cost_at_use: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="Cost per unit at time of use (snapshot for historical accuracy)",
    )

    # Context
    usage_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="production",
        server_default="production",
        comment="Type of usage (production, adjustment, waste, return)",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Usage notes or reason for adjustment",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant")
    consumable_type: Mapped["ConsumableType"] = relationship(
        "ConsumableType",
        back_populates="usage_logs",
    )
    production_run: Mapped[Optional["ProductionRun"]] = relationship(
        "ProductionRun",
    )
    model: Mapped[Optional["Model"]] = relationship(
        "Model",
    )

    def __repr__(self) -> str:
        return f"<ConsumableUsage(type={self.consumable_type_id}, qty={self.quantity_used})>"

    @property
    def total_cost(self) -> float:
        """Calculate total cost of this usage."""
        if self.cost_at_use is None:
            return 0.0
        return self.quantity_used * float(self.cost_at_use)
