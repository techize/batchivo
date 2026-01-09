"""Designer model for tracking licensed 3D print designers."""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product


class Designer(Base, UUIDMixin, TimestampMixin):
    """
    Licensed designer for 3D print designs.

    Tracks designers whose designs are commercially licensed for printing and selling.
    Used for attribution on products and membership cost tracking.
    """

    __tablename__ = "designers"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_designer_tenant_slug"),)

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Designer identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Designer display name (e.g., PrintyJay, CinderWings)",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="URL-friendly identifier (unique per tenant)",
    )

    # Branding
    logo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to designer logo image",
    )

    website_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Designer website or store URL",
    )

    social_links: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Social media links as JSON (e.g., {instagram: url, youtube: url})",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Designer bio/description for profile page",
    )

    # Membership tracking (internal use)
    membership_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Annual/monthly membership cost",
    )

    membership_start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="When membership started",
    )

    membership_renewal_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Next renewal date for membership",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether designer is currently active/licensed",
    )

    # Internal notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes about the designer/membership",
    )

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="designer",
        lazy="select",  # Use lazy load to avoid loading all products by default
    )

    def __repr__(self) -> str:
        return f"<Designer {self.name} ({self.slug})>"
