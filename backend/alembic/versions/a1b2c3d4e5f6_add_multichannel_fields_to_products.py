"""Add multi-channel publishing fields to products.

Revision ID: a1b2c3d4e5f6
Revises: z3a4b5c6d7e8
Create Date: 2026-03-17 00:00:00.000000

Adds tags, product_type, seo_slug/title/description, material, colour_options,
and etsy_taxonomy_id to support Shopify and Etsy sync.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}", nullable=True,
                  comment="Keyword tags for Shopify/Etsy discoverability"),
    )
    op.add_column(
        "products",
        sa.Column("product_type", sa.String(100), nullable=True,
                  comment="Product type for Shopify product_type field (e.g. '3D Print')"),
    )
    op.add_column(
        "products",
        sa.Column("seo_slug", sa.String(200), nullable=True,
                  comment="URL-friendly handle for canonical URLs"),
    )
    op.add_column(
        "products",
        sa.Column("seo_title", sa.String(200), nullable=True,
                  comment="SEO meta title (≤60 chars)"),
    )
    op.add_column(
        "products",
        sa.Column("seo_description", sa.String(300), nullable=True,
                  comment="SEO meta description (≤155 chars)"),
    )
    op.add_column(
        "products",
        sa.Column("material", sa.String(100), nullable=True,
                  comment="Primary material (e.g. 'PLA')"),
    )
    op.add_column(
        "products",
        sa.Column("colour_options", postgresql.ARRAY(sa.String()), nullable=True,
                  comment="Available filament colour options"),
    )
    op.add_column(
        "products",
        sa.Column("etsy_taxonomy_id", sa.Integer(), nullable=True,
                  comment="Etsy taxonomy integer ID"),
    )
    op.create_index("ix_products_seo_slug", "products", ["seo_slug"])


def downgrade() -> None:
    op.drop_index("ix_products_seo_slug", table_name="products")
    op.drop_column("products", "etsy_taxonomy_id")
    op.drop_column("products", "colour_options")
    op.drop_column("products", "material")
    op.drop_column("products", "seo_description")
    op.drop_column("products", "seo_title")
    op.drop_column("products", "seo_slug")
    op.drop_column("products", "product_type")
    op.drop_column("products", "tags")
