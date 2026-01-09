"""Customer models for shop user accounts.

Customers are separate from Users (admin/staff accounts).
Each customer account is tenant-specific (per-shop).
"""

import secrets
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

import bcrypt
from sqlalchemy import Boolean, ForeignKey, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.order import Order


class Customer(Base, UUIDMixin, TimestampMixin):
    """
    Customer represents a shop customer who can create an account.

    Customers are per-tenant (each shop has its own customer base).
    A person shopping at multiple shops would have separate accounts.
    """

    __tablename__ = "customers"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Customer email address (unique per tenant)",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt hashed password",
    )

    # Profile
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Customer full name",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Customer phone number",
    )

    # Email verification
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether email address is verified",
    )
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When email was verified",
    )
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email verification token",
    )
    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When verification token expires",
    )

    # Password reset
    reset_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Password reset token",
    )
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When reset token expires",
    )

    # Marketing preferences
    marketing_consent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether customer consented to marketing emails",
    )
    marketing_consent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When marketing consent was given",
    )

    # Activity tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last login timestamp",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether customer account is active",
    )

    # Relationships
    addresses: Mapped[List["CustomerAddress"]] = relationship(
        "CustomerAddress",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="customer",
        lazy="noload",  # Don't auto-load orders, use explicit query
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_customer_tenant_email"),
        {"comment": "Customer accounts for shop storefronts"},
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, email='{self.email}')>"

    def verify_password(self, plain_password: str) -> bool:
        """Verify a plain password against the hashed password."""
        if not self.hashed_password:
            return False
        return bcrypt.checkpw(plain_password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    def set_password(self, plain_password: str) -> None:
        """Hash and set the customer's password."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        self.hashed_password = hashed.decode("utf-8")

    def generate_verification_token(self) -> str:
        """Generate a new email verification token."""
        token = secrets.token_urlsafe(32)
        self.email_verification_token = token
        return token

    def generate_reset_token(self) -> str:
        """Generate a new password reset token."""
        token = secrets.token_urlsafe(32)
        self.reset_token = token
        return token


class CustomerAddress(Base, UUIDMixin, TimestampMixin):
    """
    CustomerAddress stores saved addresses for a customer.

    Customers can save multiple addresses (home, work, etc.)
    with one marked as default for checkout convenience.
    """

    __tablename__ = "customer_addresses"

    # Customer reference
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Customer ID",
    )

    # Tenant for easier querying
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Address label
    label: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Home",
        comment="Address label (Home, Work, etc.)",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is the default address",
    )

    # Contact name (may differ from customer name)
    recipient_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Recipient name for this address",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Contact phone for this address",
    )

    # Address fields
    line1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Address line 1",
    )
    line2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Address line 2",
    )
    city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="City",
    )
    county: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="County/State",
    )
    postcode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Postcode/ZIP",
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="United Kingdom",
        comment="Country",
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="addresses",
    )

    def __repr__(self) -> str:
        return f"<CustomerAddress(id={self.id}, label='{self.label}')>"
