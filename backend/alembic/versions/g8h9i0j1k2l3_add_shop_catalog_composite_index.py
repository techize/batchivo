"""Add composite index for shop products catalog query

Revision ID: g8h9i0j1k2l3
Revises: e1d9c135aa30
Create Date: 2026-03-29 04:30:00.000000

The shop /products endpoint filters by (tenant_id, is_active, shop_visible).
Individual indexes exist on tenant_id and shop_visible, but no composite index
covers the combined filter. PostgreSQL must intersect two index scans or fall
back to a sequential scan as the products table grows.

This composite index covers the exact WHERE clause used by get_products():
  WHERE tenant_id = $1 AND is_active = true AND shop_visible = true
Including created_at as a trailing key eliminates the post-filter sort for the
default newest-first order.
"""

from alembic import op


revision = "g8h9i0j1k2l3"
down_revision = "e1d9c135aa30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_products_shop_catalog",
        "products",
        ["tenant_id", "is_active", "shop_visible", "created_at"],
        postgresql_where="is_active = true AND shop_visible = true",
    )


def downgrade() -> None:
    op.drop_index("idx_products_shop_catalog", table_name="products")
