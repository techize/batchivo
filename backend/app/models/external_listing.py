"""ExternalListing model for tracking product listings on external marketplaces."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ExternalListing(Base, UUIDMixin, TimestampMixin):
    """
    Tracks product listings on external marketplaces (Etsy, eBay, Amazon, etc.).

    Nozzly is ALWAYS the source of truth. Sync operations always overwrite
    external systems with Nozzly data - no merge, no conflict resolution.

    Each product can have one listing per platform.
    """

    __tablename__ = "external_listings"

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
        comment="Product this listing belongs to",
    )

    # Platform identification
    platform: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Platform name: etsy, ebay, amazon, shopify",
    )

    # External reference
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="External listing ID on the platform (e.g., Etsy listing_id)",
    )

    external_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to the listing on the external platform",
    )

    # Sync status
    sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="synced",
        comment="Sync status: synced, pending, error",
    )

    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When the listing was last synced to the platform",
    )

    last_sync_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message from last failed sync attempt",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="external_listings",
        lazy="selectin",
    )

    # Constraints and indexes
    __table_args__ = (
        # One listing per product per platform
        UniqueConstraint("product_id", "platform", name="uq_external_listing_product_platform"),
        # Index for finding listings by platform
        Index("ix_external_listings_platform_tenant", "platform", "tenant_id"),
        {"comment": "Product listings on external marketplaces (Etsy, eBay, etc.)"},
    )

    def __repr__(self) -> str:
        return f"<ExternalListing(product_id={self.product_id}, platform={self.platform}, external_id={self.external_id})>"
