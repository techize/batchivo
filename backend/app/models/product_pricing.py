"""ProductPricing model - pricing per product per sales channel."""

import uuid
from typing import TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.sales_channel import SalesChannel


class ProductPricing(Base, UUIDMixin, TimestampMixin):
    """
    Pricing for a Product on a specific Sales Channel.

    Each product can have different prices on different channels.
    Platform fees are calculated from the channel's fee structure.
    """

    __tablename__ = "product_pricing"

    # References
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Product being priced",
    )

    sales_channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Sales channel for this price",
    )

    # Pricing
    list_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Listed selling price",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether this pricing is active (product listed on this channel)",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="pricing",
    )

    sales_channel: Mapped["SalesChannel"] = relationship(
        "SalesChannel",
        back_populates="pricing",
        lazy="joined",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("product_id", "sales_channel_id", name="uq_product_channel_pricing"),
        {"comment": "Product pricing per sales channel"},
    )

    def __repr__(self) -> str:
        return f"<ProductPricing(product_id={self.product_id}, channel_id={self.sales_channel_id}, price={self.list_price})>"

    def calculate_profit(self, make_cost: float) -> dict:
        """
        Calculate profit for this product on this channel.

        Args:
            make_cost: Total cost to make the product

        Returns:
            dict with:
            - list_price: What customer pays
            - platform_fee: Fee charged by platform
            - net_revenue: After platform fees
            - profit: Net revenue minus make cost
            - margin_percentage: Profit as % of list price
        """
        list_price = Decimal(str(self.list_price))
        platform_fee = Decimal(str(self.sales_channel.calculate_platform_fee(float(list_price))))
        net_revenue = list_price - platform_fee
        make = Decimal(str(make_cost))
        profit = net_revenue - make

        margin_pct = (profit / list_price * 100) if list_price > 0 else Decimal("0")

        return {
            "list_price": float(list_price),
            "platform_fee": float(platform_fee),
            "net_revenue": float(net_revenue),
            "profit": float(profit),
            "margin_percentage": float(margin_pct),
        }
