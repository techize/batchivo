"""Add shipped and delivered email tracking to orders.

Revision ID: z3a4b5c6d7e8
Revises: y2z3a4b5c6d7
Create Date: 2025-12-29 18:20:00.000000

This migration adds email tracking fields for shipped and delivered notifications.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "z3a4b5c6d7e8"
down_revision = "y2z3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add shipped email tracking columns
    op.add_column(
        "orders",
        sa.Column(
            "shipped_email_sent",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether shipped notification email was sent successfully",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "shipped_email_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When shipped email was sent",
        ),
    )

    # Add delivered email tracking columns
    op.add_column(
        "orders",
        sa.Column(
            "delivered_email_sent",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether delivered notification email was sent successfully",
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "delivered_email_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When delivered email was sent",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "delivered_email_sent_at")
    op.drop_column("orders", "delivered_email_sent")
    op.drop_column("orders", "shipped_email_sent_at")
    op.drop_column("orders", "shipped_email_sent")
