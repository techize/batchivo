"""Product review models for customer feedback and ratings.

Reviews require admin approval before being visible on the storefront.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, DateTime, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.product import Product
    from app.models.user import User


class Review(Base, UUIDMixin, TimestampMixin):
    """
    Review represents a customer review of a product.

    Reviews are per-tenant and require admin approval before display.
    Can be linked to a customer account or submitted by guests.
    """

    __tablename__ = "reviews"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Product reference
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Product being reviewed",
    )

    # Customer reference (optional - for logged-in customers)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Customer account if logged in when submitting",
    )

    # Reviewer info (stored separately in case customer deleted)
    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Reviewer email address",
    )
    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Reviewer display name",
    )

    # Review content
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Star rating (1-5)",
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Review title/headline",
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Review body text",
    )

    # Verification
    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether reviewer has purchased this product",
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Order that verified this purchase",
    )

    # Moderation
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether review is approved for display",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When review was approved",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin user who approved the review",
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason for rejection if not approved",
    )

    # Engagement
    helpful_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of 'helpful' votes",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="reviews",
        lazy="selectin",
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        lazy="noload",
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="noload",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
        {"comment": "Customer product reviews with moderation"},
    )

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, product_id={self.product_id}, rating={self.rating})>"
