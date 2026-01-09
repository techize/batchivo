"""Inventory Transaction model for audit trail of inventory changes."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class TransactionType(str, Enum):
    """Types of inventory transactions."""

    PURCHASE = "purchase"  # Initial purchase/receiving
    USAGE = "usage"  # Production run consumption
    ADJUSTMENT = "adjustment"  # Manual correction
    TRANSFER = "transfer"  # Transfer between locations
    RETURN = "return"  # Return to inventory (e.g., revert completion)
    WASTE = "waste"  # Damaged/expired/discarded
    COUNT = "count"  # Physical inventory count adjustment


class InventoryTransaction(Base, UUIDMixin, TimestampMixin):
    """
    Audit trail for all inventory weight changes.

    Records every change to spool weight with before/after values,
    reason for change, and reference to source operation (e.g., production run).
    """

    __tablename__ = "inventory_transactions"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Spool reference
    spool_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("spools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Spool affected by this transaction",
    )

    # Transaction type
    transaction_type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType, native_enum=False, length=20),
        nullable=False,
        index=True,
        comment="Type of inventory transaction",
    )

    # Weight tracking (in grams)
    weight_before: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Spool weight before transaction (grams)",
    )

    weight_change: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Weight change amount (negative for usage, positive for returns)",
    )

    weight_after: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Spool weight after transaction (grams)",
    )

    # Reference to source operation
    production_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("production_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Production run that caused this transaction (if applicable)",
    )

    production_run_material_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("production_run_materials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Production run material record (if applicable)",
    )

    # User who performed the action
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who performed this transaction",
    )

    # Description and notes
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Human-readable description of the transaction",
    )

    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional notes or context",
    )

    # Metadata for additional context (named transaction_metadata to avoid SQLAlchemy reserved name)
    transaction_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",  # Use 'metadata' as the column name in DB
        JSON,
        nullable=True,
        comment="Additional metadata (variance info, run details, etc.)",
    )

    # Transaction timestamp (separate from created_at for backdating)
    transaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="When the transaction occurred",
    )

    # For reversals/corrections
    reversal_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("inventory_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID of transaction this reverses (for rollbacks)",
    )

    is_reversal: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether this transaction is a reversal of another",
    )

    # Relationships
    spool: Mapped["Spool"] = relationship(
        "Spool",
        lazy="joined",
    )

    production_run: Mapped[Optional["ProductionRun"]] = relationship(
        "ProductionRun",
        lazy="select",
        foreign_keys=[production_run_id],
    )

    production_run_material: Mapped[Optional["ProductionRunMaterial"]] = relationship(
        "ProductionRunMaterial",
        lazy="select",
        foreign_keys=[production_run_material_id],
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="select",
    )

    reversal_of: Mapped[Optional["InventoryTransaction"]] = relationship(
        "InventoryTransaction",
        remote_side="InventoryTransaction.id",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryTransaction(type={self.transaction_type.value}, "
            f"spool={self.spool_id}, change={self.weight_change}g)>"
        )

    @property
    def is_deduction(self) -> bool:
        """Returns True if this transaction reduced inventory."""
        return self.weight_change < 0

    @property
    def is_addition(self) -> bool:
        """Returns True if this transaction increased inventory."""
        return self.weight_change > 0
