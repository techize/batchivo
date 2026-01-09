"""Add email tracking fields to orders table.

Revision ID: u8v9w0x1y2z3
Revises: s6t7u8v9w0x1
Create Date: 2025-12-22 19:45:00.000000

This migration adds fields to track order confirmation email status.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "u8v9w0x1y2z3"
down_revision = "s6t7u8v9w0x1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add confirmation_email_sent boolean column
    op.add_column(
        "orders",
        sa.Column(
            "confirmation_email_sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether order confirmation email was sent successfully",
        ),
    )
    # Add confirmation_email_sent_at timestamp column
    op.add_column(
        "orders",
        sa.Column(
            "confirmation_email_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When confirmation email was sent",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "confirmation_email_sent_at")
    op.drop_column("orders", "confirmation_email_sent")
