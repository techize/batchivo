"""Add currency_code and currency_symbol fields to tenants table.

Revision ID: a4b5c6d7e8f9
Revises: z3a4b5c6d7e8
Create Date: 2026-01-19 16:00:00.000000

This migration adds currency settings to tenants for multi-currency support.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "a4b5c6d7e8f9"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add currency_code column with default GBP
    op.add_column(
        "tenants",
        sa.Column(
            "currency_code",
            sa.String(3),
            nullable=False,
            server_default="GBP",
            comment="ISO 4217 currency code (e.g., GBP, USD, EUR)",
        ),
    )

    # Add currency_symbol column with default pound sign
    op.add_column(
        "tenants",
        sa.Column(
            "currency_symbol",
            sa.String(5),
            nullable=False,
            server_default="£",
            comment="Currency symbol for display (e.g., £, $, €)",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "currency_symbol")
    op.drop_column("tenants", "currency_code")
