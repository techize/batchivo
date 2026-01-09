"""Add webhook tables

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2025-12-30 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6g7h8i9j0k1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create webhook_subscriptions and webhook_deliveries tables."""
    # Create webhook_subscriptions table
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("secret", sa.String(255), nullable=False),
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("custom_headers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        comment="Webhook subscriptions for outbound event notifications",
    )

    op.create_index(
        "ix_webhook_subscriptions_tenant_id",
        "webhook_subscriptions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_webhook_subscriptions_tenant_active",
        "webhook_subscriptions",
        ["tenant_id", "is_active"],
    )

    # Create webhook_deliveries table
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["webhook_subscriptions.id"],
            ondelete="CASCADE",
        ),
        comment="Webhook delivery attempts and responses",
    )

    op.create_index(
        "ix_webhook_deliveries_subscription_id",
        "webhook_deliveries",
        ["subscription_id"],
    )
    op.create_index(
        "ix_webhook_deliveries_event_type",
        "webhook_deliveries",
        ["event_type"],
    )
    op.create_index(
        "ix_webhook_deliveries_status",
        "webhook_deliveries",
        ["status"],
    )
    op.create_index(
        "ix_webhook_deliveries_status_retry",
        "webhook_deliveries",
        ["status", "next_retry_at"],
    )
    op.create_index(
        "ix_webhook_deliveries_subscription_created",
        "webhook_deliveries",
        ["subscription_id", "created_at"],
    )


def downgrade() -> None:
    """Drop webhook tables."""
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_subscriptions")
