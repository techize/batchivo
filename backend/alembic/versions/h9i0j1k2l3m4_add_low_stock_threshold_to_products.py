"""Add low_stock_threshold column to products table

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-03-31 20:00:00.000000

Replaces the hard-coded reorder threshold of 5 in order_fulfillment.py
with a per-product configurable value.  Existing rows get the previous
default of 5 via server_default so the behaviour is unchanged after
migration.
"""

import sqlalchemy as sa
from alembic import op


revision = "h9i0j1k2l3m4"
down_revision = "g8h9i0j1k2l3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "low_stock_threshold",
            sa.Integer(),
            nullable=False,
            server_default="5",
            comment="Units-in-stock level at or below which a low-stock alert is raised",
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "low_stock_threshold")
