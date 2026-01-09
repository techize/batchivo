"""Add platform_admin_audit_logs table.

Revision ID: b5c6d7e8f9g0
Revises: a4b5c6d7e8f9
Create Date: 2025-12-30 22:45:00.000000

This migration adds:
- platform_admin_audit_logs table for tracking platform admin actions
- Indexes on admin_user_id and created_at for query performance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "b5c6d7e8f9g0"
down_revision = "d7e8f9g0h1i2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_admin_audit_logs",
        # Primary key (UUIDMixin)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Who performed the action
        sa.Column(
            "admin_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="ID of the platform admin who performed the action",
        ),
        # What action was performed
        sa.Column(
            "action",
            sa.String(100),
            nullable=False,
            comment="Action type: impersonate, deactivate_tenant, etc.",
        ),
        # Target of the action
        sa.Column(
            "target_type",
            sa.String(50),
            nullable=True,
            comment="Type of target: tenant, user, setting",
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="ID of the target entity",
        ),
        # Additional context
        sa.Column(
            "action_metadata",
            postgresql.JSONB,
            nullable=True,
            comment="Additional context about the action",
        ),
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="IP address of the admin",
        ),
        sa.Column(
            "user_agent",
            sa.Text,
            nullable=True,
            comment="User agent string of the admin's browser",
        ),
        # Timestamp
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
            comment="When the action was performed",
        ),
    )


def downgrade() -> None:
    op.drop_table("platform_admin_audit_logs")
