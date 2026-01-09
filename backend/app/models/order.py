"""Order model for tracking customer orders from sales channels."""

import uuid
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.sales_channel import SalesChannel
    from app.models.product import Product
    from app.models.customer import Customer


class OrderStatus:
    """Order status constants."""

    PENDING = "pending"  # Payment received, awaiting processing
    PROCESSING = "processing"  # Being prepared/printed
    SHIPPED = "shipped"  # Dispatched to customer
    DELIVERED = "delivered"  # Confirmed delivered
    CANCELLED = "cancelled"  # Order cancelled
    REFUNDED = "refunded"  # Payment refunded


class Order(Base, UUIDMixin, TimestampMixin):
    """
    Order represents a customer purchase from a sales channel.

    Stores order details, customer info, shipping address, and payment info.
    Links to OrderItems for individual line items.
    """

    __tablename__ = "orders"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Order identification
    order_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="Human-readable order number (e.g., MF-20251210-001)",
    )

    # Sales channel reference
    sales_channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sales_channels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Sales channel this order came from",
    )

    # Customer reference (optional - for logged-in customers)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Customer account if logged in during purchase",
    )

    # Order status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True,
        comment="Order status: pending, processing, shipped, delivered, cancelled, refunded",
    )

    # Customer information
    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Customer email address",
    )
    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Customer full name",
    )
    customer_phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Customer phone number",
    )

    # Shipping address
    shipping_address_line1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Shipping address line 1",
    )
    shipping_address_line2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Shipping address line 2",
    )
    shipping_city: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Shipping city",
    )
    shipping_county: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Shipping county/state",
    )
    shipping_postcode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Shipping postcode",
    )
    shipping_country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="United Kingdom",
        comment="Shipping country",
    )

    # Shipping method
    shipping_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Shipping method (e.g., Royal Mail 2nd Class)",
    )
    shipping_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Shipping cost in GBP",
    )

    # Order totals
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Order subtotal before shipping",
    )
    total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Order total including shipping",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="GBP",
        comment="Currency code",
    )

    # Discount applied
    discount_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Discount code used (stored for reference)",
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Discount amount applied to this order",
    )

    # Payment information
    payment_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="square",
        comment="Payment provider (square, stripe, etc.)",
    )
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Payment provider transaction ID",
    )
    payment_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="completed",
        comment="Payment status from provider",
    )

    # Tracking
    tracking_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Shipping tracking number",
    )
    tracking_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Tracking URL",
    )
    shipped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the order was shipped",
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the order was delivered",
    )

    # Fulfillment (inventory deducted)
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When inventory was deducted for this order",
    )

    # Email tracking
    confirmation_email_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether order confirmation email was sent successfully",
    )
    confirmation_email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When confirmation email was sent",
    )
    shipped_email_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether shipped notification email was sent successfully",
    )
    shipped_email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When shipped email was sent",
    )
    delivered_email_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether delivered notification email was sent successfully",
    )
    delivered_email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When delivered email was sent",
    )

    # Notes
    customer_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes from customer",
    )
    internal_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes for staff",
    )

    # Relationships
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sales_channel: Mapped[Optional["SalesChannel"]] = relationship(
        "SalesChannel",
        lazy="selectin",
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="orders",
        lazy="noload",
    )


class OrderItem(Base, UUIDMixin, TimestampMixin):
    """
    OrderItem represents a single line item in an order.

    Links to Product for inventory tracking and stores the
    price at time of purchase (which may differ from current price).
    """

    __tablename__ = "order_items"

    # Tenant isolation (denormalized from Order for RLS and direct queries)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Order reference
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent order ID",
    )

    # Product reference (nullable for products that may be deleted)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Product ID (may be null if product deleted)",
    )

    # Product snapshot (stored at time of order)
    product_sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Product SKU at time of order",
    )
    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Product name at time of order",
    )

    # Quantity and pricing
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Quantity ordered",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Price per unit at time of order",
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total line item price (quantity * unit_price)",
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )
    product: Mapped[Optional["Product"]] = relationship(
        "Product",
        lazy="selectin",
    )
