"""Category model for product categorization."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product


# Many-to-many association table for products and categories
# Includes tenant_id for multi-tenant isolation and RLS enforcement
product_categories = Table(
    "product_categories",
    Base.metadata,
    Column("tenant_id", ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("product_id", ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base, UUIDMixin, TimestampMixin):
    """
    Category for organizing products in the shop.

    Categories enable filtering and navigation in the storefront.
    Products can belong to multiple categories (many-to-many relationship).
    """

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_category_tenant_slug"),)

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Category identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Category display name",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="URL-friendly identifier (unique per tenant)",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Category description",
    )

    # Display settings
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Sort order for display (lower = first)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether category is visible in shop",
    )

    # Shop display
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Hero/banner image URL for category page in shop",
    )

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product",
        secondary=product_categories,
        back_populates="categories",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Category {self.name} ({self.slug})>"
