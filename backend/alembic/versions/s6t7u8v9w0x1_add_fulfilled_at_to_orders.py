"""Add fulfilled_at column to orders table.

Revision ID: s6t7u8v9w0x1
Revises: t7u8v9w0x1y2
Create Date: 2025-12-19 21:30:00.000000

This migration adds the fulfilled_at timestamp to track when
inventory was deducted for an order (separate from shipped_at).
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "s6t7u8v9w0x1"
down_revision = "t7u8v9w0x1y2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add fulfilled_at column to orders table
    op.add_column(
        "orders",
        sa.Column(
            "fulfilled_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When inventory was deducted for this order",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "fulfilled_at")
