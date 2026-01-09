"""Discount code model for promotional pricing."""

import uuid
from typing import Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class DiscountType(str, Enum):
    """Type of discount to apply."""

    PERCENTAGE = "percentage"  # Discount as percentage of order (0-100)
    FIXED_AMOUNT = "fixed_amount"  # Fixed amount off order total


class DiscountCode(Base, UUIDMixin, TimestampMixin):
    """
    DiscountCode represents a promotional discount that can be applied to orders.

    Supports both percentage-based and fixed amount discounts with various
    constraints like usage limits, minimum order amounts, and validity periods.
    """

    __tablename__ = "discount_codes"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Code identification
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Discount code (uppercase, unique per tenant)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name for the discount",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal description of the discount",
    )

    # Discount configuration
    discount_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of discount: percentage or fixed_amount",
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Discount amount (percentage 0-100 or fixed amount in GBP)",
    )

    # Constraints
    min_order_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Minimum order subtotal required to use this discount",
    )
    max_discount_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Maximum discount amount (caps percentage discounts)",
    )

    # Usage limits
    max_uses: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum total uses (null = unlimited)",
    )
    max_uses_per_customer: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum uses per customer email (null = unlimited)",
    )
    current_uses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Current number of times this code has been used",
    )

    # Validity period
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Start of validity period",
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="End of validity period (null = no expiry)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the discount is currently active",
    )

    # Unique constraint: code must be unique per tenant
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_discount_code_tenant"),
        {"comment": "Discount codes for promotional pricing"},
    )


class DiscountUsage(Base, UUIDMixin, TimestampMixin):
    """
    DiscountUsage tracks individual uses of discount codes.

    Used for enforcing per-customer usage limits and audit trails.
    """

    __tablename__ = "discount_usages"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # References
    discount_code_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("discount_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The discount code that was used",
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The order this discount was applied to",
    )

    # Customer identification
    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Customer email for per-customer limit tracking",
    )

    # Applied discount
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Actual discount amount applied to this order",
    )
