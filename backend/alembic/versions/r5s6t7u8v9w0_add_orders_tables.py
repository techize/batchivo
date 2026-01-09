"""Add orders and order_items tables.

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2024-12-10 20:00:00.000000

This migration adds tables for tracking customer orders from sales channels.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "r5s6t7u8v9w0"
down_revision = "q4r5s6t7u8v9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================
    # Orders table
    # ========================================
    op.create_table(
        "orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_number", sa.String(50), nullable=False),
        sa.Column("sales_channel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        # Customer info
        sa.Column("customer_email", sa.String(255), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("customer_phone", sa.String(50), nullable=True),
        # Shipping address
        sa.Column("shipping_address_line1", sa.String(255), nullable=False),
        sa.Column("shipping_address_line2", sa.String(255), nullable=True),
        sa.Column("shipping_city", sa.String(100), nullable=False),
        sa.Column("shipping_county", sa.String(100), nullable=True),
        sa.Column("shipping_postcode", sa.String(20), nullable=False),
        sa.Column(
            "shipping_country", sa.String(100), nullable=False, server_default="United Kingdom"
        ),
        # Shipping method
        sa.Column("shipping_method", sa.String(100), nullable=False),
        sa.Column("shipping_cost", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        # Totals
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        # Payment
        sa.Column("payment_provider", sa.String(50), nullable=False, server_default="square"),
        sa.Column("payment_id", sa.String(255), nullable=True),
        sa.Column("payment_status", sa.String(50), nullable=False, server_default="completed"),
        # Tracking
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("tracking_url", sa.String(500), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        # Notes
        sa.Column("customer_notes", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sales_channel_id"], ["sales_channels.id"], ondelete="SET NULL"),
    )

    # Indexes for orders
    op.create_index("idx_orders_tenant", "orders", ["tenant_id"])
    op.create_index("idx_orders_order_number", "orders", ["order_number"], unique=True)
    op.create_index("idx_orders_status", "orders", ["status"])
    op.create_index("idx_orders_payment_id", "orders", ["payment_id"])
    op.create_index("idx_orders_sales_channel", "orders", ["sales_channel_id"])
    op.create_index("idx_orders_created_at", "orders", ["created_at"])

    # ========================================
    # Order Items table
    # ========================================
    op.create_table(
        "order_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Product snapshot
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        # Quantity and pricing
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(10, 2), nullable=False),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
    )

    # Indexes for order_items
    op.create_index("idx_order_items_order", "order_items", ["order_id"])
    op.create_index("idx_order_items_product", "order_items", ["product_id"])


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_table("orders")
