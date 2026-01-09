"""Return request (RMA) models for handling product returns.

Supports customer-initiated returns with admin approval workflow.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order import Order, OrderItem


class ReturnStatus(str, enum.Enum):
    """Status of a return request."""

    REQUESTED = "requested"  # Customer submitted request
    APPROVED = "approved"  # Admin approved, awaiting item return
    RECEIVED = "received"  # Item received back
    COMPLETED = "completed"  # Refund/replacement processed
    REJECTED = "rejected"  # Request rejected by admin
    CANCELLED = "cancelled"  # Cancelled by customer


class ReturnReason(str, enum.Enum):
    """Reason for return."""

    DEFECTIVE = "defective"  # Product is defective/broken
    WRONG_ITEM = "wrong_item"  # Received wrong item
    NOT_AS_DESCRIBED = "not_as_described"  # Product doesn't match description
    CHANGED_MIND = "changed_mind"  # Customer changed their mind
    DAMAGED_SHIPPING = "damaged_shipping"  # Damaged during shipping
    MISSING_PARTS = "missing_parts"  # Missing parts/pieces
    OTHER = "other"  # Other reason


class ReturnAction(str, enum.Enum):
    """Requested resolution action."""

    REFUND = "refund"  # Full refund
    REPLACEMENT = "replacement"  # Replace with same item
    REPAIR = "repair"  # Repair the item
    STORE_CREDIT = "store_credit"  # Store credit


class ReturnRequest(Base, UUIDMixin, TimestampMixin):
    """
    ReturnRequest represents a customer's request to return products.

    Supports multi-item returns from a single order with admin workflow.
    """

    __tablename__ = "return_requests"
    __table_args__ = (
        UniqueConstraint("tenant_id", "rma_number", name="uq_return_request_tenant_rma"),
    )

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # RMA identification
    rma_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="RMA number (e.g., RMA-20251229-001)",
    )

    # Order reference
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Order being returned",
    )

    # Customer reference (optional - for logged-in customers)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Customer account if logged in",
    )

    # Customer info (stored separately in case no account)
    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Customer email address",
    )
    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Customer name",
    )

    # Return details
    status: Mapped[ReturnStatus] = mapped_column(
        Enum(ReturnStatus),
        nullable=False,
        default=ReturnStatus.REQUESTED,
        index=True,
        comment="Current status of return request",
    )
    reason: Mapped[ReturnReason] = mapped_column(
        Enum(ReturnReason),
        nullable=False,
        comment="Reason for return",
    )
    reason_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Additional details about the reason",
    )
    requested_action: Mapped[ReturnAction] = mapped_column(
        Enum(ReturnAction),
        nullable=False,
        default=ReturnAction.REFUND,
        comment="What customer wants (refund, replacement, etc.)",
    )

    # Admin notes
    admin_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes from admin",
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for rejection if rejected",
    )

    # Workflow timestamps
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When request was approved",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin who approved",
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When returned items were received",
    )
    received_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin who marked as received",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When refund/replacement was completed",
    )
    completed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin who completed",
    )

    # Resolution
    refund_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Amount refunded (if applicable)",
    )
    refund_reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Payment provider refund reference",
    )
    replacement_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="Replacement order if created",
    )

    # Return shipping
    return_tracking_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Tracking number for return shipment",
    )
    return_label_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to return shipping label",
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        foreign_keys=[order_id],
        lazy="selectin",
    )
    replacement_order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[replacement_order_id],
        lazy="noload",
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        lazy="noload",
    )
    items: Mapped[List["ReturnItem"]] = relationship(
        "ReturnItem",
        back_populates="return_request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ReturnRequest(rma={self.rma_number}, status={self.status})>"


class ReturnItem(Base, UUIDMixin, TimestampMixin):
    """
    ReturnItem represents a single item being returned.

    Links to order item with quantity and optional reason.
    """

    __tablename__ = "return_items"

    # Return request reference
    return_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("return_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent return request",
    )

    # Order item reference
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Order item being returned",
    )

    # Quantity
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Quantity being returned",
    )

    # Item-specific reason (if different from request)
    reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Item-specific reason for return",
    )

    # Condition when received
    condition_notes: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Notes on item condition when received",
    )
    is_restockable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether item can be restocked",
    )

    # Relationships
    return_request: Mapped["ReturnRequest"] = relationship(
        "ReturnRequest",
        back_populates="items",
    )
    order_item: Mapped["OrderItem"] = relationship(
        "OrderItem",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ReturnItem(id={self.id}, quantity={self.quantity})>"
