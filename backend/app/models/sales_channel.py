"""SalesChannel model for marketplace/selling platform tracking."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product_pricing import ProductPricing


class SalesChannel(Base, UUIDMixin, TimestampMixin):
    """
    Sales Channel represents where products are sold.

    Examples: Craft fairs, Etsy, eBay, Shopify store, direct sales
    Each channel can have different fee structures (percentage, fixed, or both).
    """

    __tablename__ = "sales_channels"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Channel identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Channel name (e.g., 'Milton Keynes Craft Fair', 'Etsy Store')",
    )

    platform_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Platform type: fair, online_shop, shopify, ebay, etsy, amazon, other",
    )

    # Fee structure
    fee_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0,
        server_default="0",
        comment="Platform percentage fee (e.g., 5.0 = 5%)",
    )

    fee_fixed: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
        comment="Fixed fee per transaction (e.g., £0.30)",
    )

    monthly_cost: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
        comment="Monthly subscription/booth fee",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether channel is active",
    )

    # Relationships
    pricing: Mapped[list["ProductPricing"]] = relationship(
        "ProductPricing",
        back_populates="sales_channel",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_sales_channel_tenant_name"),
        CheckConstraint(
            "platform_type IN ('fair', 'online_shop', 'shopify', 'ebay', 'etsy', 'amazon', 'other')",
            name="check_platform_type",
        ),
        {"comment": "Sales channels/marketplaces with fee structures"},
    )

    def __repr__(self) -> str:
        return f"<SalesChannel(name={self.name}, platform={self.platform_type})>"

    def calculate_platform_fee(self, list_price: float) -> float:
        """Calculate total platform fee for a given list price."""
        percentage_fee = list_price * (float(self.fee_percentage) / 100)
        return percentage_fee + float(self.fee_fixed)
