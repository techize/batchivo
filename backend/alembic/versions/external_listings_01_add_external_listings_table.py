"""Add external_listings table for marketplace integrations

Revision ID: external_listings_01
Revises: product_specs_01
Create Date: 2026-01-13 09:10:00.000000

Adds table to track product listings on external marketplaces (Etsy, eBay, Amazon).
Nozzly is the source of truth - sync always overwrites external systems.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "external_listings_01"
down_revision: Union[str, None] = "product_specs_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_listings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("external_url", sa.String(500), nullable=True),
        sa.Column("sync_status", sa.String(20), nullable=False, server_default="synced"),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_id", "platform", name="uq_external_listing_product_platform"),
        comment="Product listings on external marketplaces (Etsy, eBay, etc.)",
    )

    # Create indexes
    op.create_index("ix_external_listings_tenant_id", "external_listings", ["tenant_id"])
    op.create_index("ix_external_listings_product_id", "external_listings", ["product_id"])
    op.create_index("ix_external_listings_platform", "external_listings", ["platform"])
    op.create_index(
        "ix_external_listings_platform_tenant", "external_listings", ["platform", "tenant_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_external_listings_platform_tenant", table_name="external_listings")
    op.drop_index("ix_external_listings_platform", table_name="external_listings")
    op.drop_index("ix_external_listings_product_id", table_name="external_listings")
    op.drop_index("ix_external_listings_tenant_id", table_name="external_listings")
    op.drop_table("external_listings")
