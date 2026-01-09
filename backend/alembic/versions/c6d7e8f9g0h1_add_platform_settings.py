"""Add platform_settings table.

Revision ID: c6d7e8f9g0h1
Revises: b5c6d7e8f9g0
Create Date: 2025-12-30 23:00:00.000000

This migration adds:
- platform_settings table for global platform configuration
- Seed data for default settings
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "c6d7e8f9g0h1"
down_revision = "b5c6d7e8f9g0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        # Primary key is the setting key
        sa.Column(
            "key",
            sa.String(100),
            primary_key=True,
            comment="Unique setting identifier",
        ),
        # Value stored as JSON
        sa.Column(
            "value",
            postgresql.JSON,
            nullable=False,
            comment="Setting value (JSON)",
        ),
        # Documentation
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Human-readable description of the setting",
        ),
        # Audit fields
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
            comment="When the setting was last updated",
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="ID of the admin who last updated this setting",
        ),
    )

    # Seed default settings
    op.execute("""
        INSERT INTO platform_settings (key, value, description) VALUES
        ('require_email_verification', 'true', 'Require email verification for new tenant registrations'),
        ('default_tenant_type', '"three_d_print"', 'Default tenant type for new registrations'),
        ('maintenance_mode', 'false', 'Enable platform-wide maintenance mode'),
        ('allow_self_registration', 'true', 'Allow users to self-register new tenants'),
        ('max_tenants_per_user', '5', 'Maximum number of tenants a user can own')
    """)


def downgrade() -> None:
    op.drop_table("platform_settings")
