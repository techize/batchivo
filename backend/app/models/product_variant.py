"""Product variant model for sized products."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ProductSizeSystem(str, Enum):
    """Size system for products."""

    NONE = "none"  # No sizing (single size)
    ACCESSORY = "accessory"  # S, M, L (hats, gloves, scarves)
    BABY_CHILD = "baby_child"  # Preemie through 12y
    ADULT_GENERAL = "adult_general"  # XS through 3XL
    ADULT_NUMERIC = "adult_numeric"  # Numeric sizes (US 2-16, UK 6-18)
    CUSTOM = "custom"  # Custom size options


# Size presets for each system
SIZE_PRESETS = {
    ProductSizeSystem.NONE: [],
    ProductSizeSystem.ACCESSORY: ["S", "M", "L"],
    ProductSizeSystem.BABY_CHILD: [
        "Preemie",
        "Newborn",
        "0-3m",
        "3-6m",
        "6-12m",
        "12-18m",
        "18-24m",
        "2-3y",
        "3-4y",
        "4-5y",
        "6-8y",
        "8-10y",
        "10-12y",
    ],
    ProductSizeSystem.ADULT_GENERAL: ["XS", "S", "M", "L", "XL", "2XL", "3XL"],
    ProductSizeSystem.ADULT_NUMERIC: [
        "US 2/UK 6",
        "US 4/UK 8",
        "US 6/UK 10",
        "US 8/UK 12",
        "US 10/UK 14",
        "US 12/UK 16",
        "US 14/UK 18",
        "US 16/UK 20",
    ],
    ProductSizeSystem.CUSTOM: [],  # User provides custom sizes
}


def get_size_options(size_system: ProductSizeSystem) -> list[str]:
    """Get size options for a size system."""
    return SIZE_PRESETS.get(size_system, [])


class ProductVariant(Base, UUIDMixin, TimestampMixin):
    """
    Product variant representing a sized version of a product.

    Each variant has its own:
    - Size identifier
    - SKU (auto-generated as {base_sku}-{size})
    - Price adjustment from base price
    - Stock quantity
    - Yarn/material requirements for knitting

    For 3D printing, variants typically don't change cost.
    For knitting, different sizes need different yarn amounts.
    """

    __tablename__ = "product_variants"

    # Tenant isolation (for consistency with other models and RLS)
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
        comment="Reference to the parent product",
    )

    # Size identifier
    size: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Size value (e.g., 'M', '6-12m', 'XL')",
    )

    # Display order for sorting sizes
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Order for display (lower = first)",
    )

    # Variant SKU (auto-generated: {product.sku}-{size})
    sku: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
        comment="Variant SKU (typically base-sku-size)",
    )

    # Price adjustment (can be positive or negative)
    price_adjustment_pence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Price adjustment from base in pence (can be negative)",
    )

    # Stock tracking per variant
    units_in_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Units in stock for this variant",
    )

    # Material requirements for knitting (JSONB)
    # Format: {"yarn_yardage": 500, "notes": "Use DK weight", "needle_size_mm": 4.0}
    yarn_requirements: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSONB with yarn/material requirements for this size",
    )

    # Make cost override (for when size significantly affects cost)
    make_cost_override_pence: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Override make cost for this variant (null = use base calculation)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether this variant is available",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        back_populates="variants",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("product_id", "size", name="uq_variant_product_size"),
        UniqueConstraint("product_id", "sku", name="uq_variant_product_sku"),
        {"comment": "Size variants for products (especially for knitting items)"},
    )

    def __repr__(self) -> str:
        return f"<ProductVariant(sku={self.sku}, size={self.size})>"

    def generate_sku(self, base_sku: str) -> str:
        """Generate variant SKU from base product SKU and size."""
        # Normalize size for SKU (remove spaces, use uppercase)
        size_slug = self.size.upper().replace(" ", "-").replace("/", "-")
        return f"{base_sku}-{size_slug}"
