"""Add is_platform_admin column to users table.

Revision ID: d7e8f9g0h1i2
Revises: y2z3a4b5c6d7
Create Date: 2025-12-30 22:30:00.000000

This migration adds:
- is_platform_admin boolean column to users table (default: false)
- Sets jonathan@techize.co.uk as platform admin
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "d7e8f9g0h1i2"
down_revision = "y2z3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_platform_admin column with server default
    op.add_column(
        "users",
        sa.Column(
            "is_platform_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether user has platform-wide admin access",
        ),
    )

    # Set jonathan@techize.co.uk as platform admin
    op.execute("UPDATE users SET is_platform_admin = true WHERE email = 'jonathan@techize.co.uk'")


def downgrade() -> None:
    op.drop_column("users", "is_platform_admin")
