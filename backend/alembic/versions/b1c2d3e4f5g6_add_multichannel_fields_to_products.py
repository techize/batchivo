"""Add multi-channel publishing fields to products.

Revision ID: b1c2d3e4f5g6
Revises: z3a4b5c6d7e8
Create Date: 2026-03-17 00:00:00.000000

Adds tags, product_type, seo_slug/title/description, material, colour_options,
and etsy_taxonomy_id to support Shopify and Etsy sync.

NOTE: These columns were applied directly via psql on 2026-03-17 before the
migration was properly tracked. The upgrade() uses ADD COLUMN IF NOT EXISTS
to be idempotent for that production database.
"""

from alembic import op


# revision identifiers
revision = "b1c2d3e4f5g6"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS throughout — columns already exist in production (applied
    # directly via psql on 2026-03-17 before this migration was properly tracked).
    op.execute(
        """
        ALTER TABLE products
            ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS product_type VARCHAR(100),
            ADD COLUMN IF NOT EXISTS seo_slug VARCHAR(200),
            ADD COLUMN IF NOT EXISTS seo_title VARCHAR(200),
            ADD COLUMN IF NOT EXISTS seo_description VARCHAR(300),
            ADD COLUMN IF NOT EXISTS material VARCHAR(100),
            ADD COLUMN IF NOT EXISTS colour_options TEXT[],
            ADD COLUMN IF NOT EXISTS etsy_taxonomy_id INTEGER
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_seo_slug ON products (seo_slug)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_seo_slug")
    op.execute(
        """
        ALTER TABLE products
            DROP COLUMN IF EXISTS etsy_taxonomy_id,
            DROP COLUMN IF EXISTS colour_options,
            DROP COLUMN IF EXISTS material,
            DROP COLUMN IF EXISTS seo_description,
            DROP COLUMN IF EXISTS seo_title,
            DROP COLUMN IF EXISTS seo_slug,
            DROP COLUMN IF EXISTS product_type,
            DROP COLUMN IF EXISTS tags
        """
    )
