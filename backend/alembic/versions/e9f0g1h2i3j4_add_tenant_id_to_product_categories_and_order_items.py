"""Add tenant_id to product_categories and order_items for multi-tenant isolation.

Revision ID: e9f0g1h2i3j4
Revises: z3a4b5c6d7e8
Create Date: 2025-12-31 16:30:00.000000

This migration adds tenant_id to:
- product_categories association table (for RLS enforcement)
- order_items table (denormalized from orders for direct query isolation)

For existing data, tenant_id is populated from the related parent tables.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "e9f0g1h2i3j4"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table_name AND column_name = :column_name)"
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    # Add tenant_id to product_categories association table
    # Skip if already exists
    if not column_exists("product_categories", "tenant_id"):
        op.add_column(
            "product_categories",
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                comment="Tenant ID for multi-tenant isolation",
            ),
        )

        # Populate tenant_id from products table
        op.execute("""
            UPDATE product_categories pc
            SET tenant_id = p.tenant_id
            FROM products p
            WHERE pc.product_id = p.id
        """)

        # Now make tenant_id non-nullable
        op.alter_column(
            "product_categories",
            "tenant_id",
            nullable=False,
        )

        # Add foreign key constraint
        op.create_foreign_key(
            "fk_product_categories_tenant_id",
            "product_categories",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # Add index for tenant_id
        op.create_index(
            "ix_product_categories_tenant_id",
            "product_categories",
            ["tenant_id"],
        )

    # Add tenant_id to order_items table
    # Skip if already exists
    if not column_exists("order_items", "tenant_id"):
        op.add_column(
            "order_items",
            sa.Column(
                "tenant_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                comment="Tenant ID for multi-tenant isolation",
            ),
        )

        # Populate tenant_id from orders table
        op.execute("""
            UPDATE order_items oi
            SET tenant_id = o.tenant_id
            FROM orders o
            WHERE oi.order_id = o.id
        """)

        # Now make tenant_id non-nullable
        op.alter_column(
            "order_items",
            "tenant_id",
            nullable=False,
        )

        # Add foreign key constraint
        op.create_foreign_key(
            "fk_order_items_tenant_id",
            "order_items",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # Add index for tenant_id
        op.create_index(
            "ix_order_items_tenant_id",
            "order_items",
            ["tenant_id"],
        )


def downgrade() -> None:
    # Remove from order_items
    if column_exists("order_items", "tenant_id"):
        op.drop_index("ix_order_items_tenant_id", table_name="order_items")
        op.drop_constraint("fk_order_items_tenant_id", "order_items", type_="foreignkey")
        op.drop_column("order_items", "tenant_id")

    # Remove from product_categories
    if column_exists("product_categories", "tenant_id"):
        op.drop_index("ix_product_categories_tenant_id", table_name="product_categories")
        op.drop_constraint(
            "fk_product_categories_tenant_id", "product_categories", type_="foreignkey"
        )
        op.drop_column("product_categories", "tenant_id")
