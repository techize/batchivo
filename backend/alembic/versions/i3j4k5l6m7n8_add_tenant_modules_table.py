"""Add tenant_modules table for module access control.

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-01-04 14:45:00.000000

This migration adds tenant_modules table to control which modules
are enabled/disabled per tenant. Allows platform admins to customize
module access for each tenant.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "i3j4k5l6m7n8"
down_revision = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table_name)"
        ),
        {"table_name": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Create tenant_modules table."""
    # Skip if already exists
    if table_exists("tenant_modules"):
        return

    op.create_table(
        "tenant_modules",
        # Primary key (UUIDMixin)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Tenant isolation
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant this module configuration belongs to",
        ),
        # Module identification
        sa.Column(
            "module_name",
            sa.String(50),
            nullable=False,
            comment="Module identifier (e.g., 'spools', 'models', 'printers')",
        ),
        # Enabled status
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether this module is enabled for the tenant",
        ),
        # Audit trail
        sa.Column(
            "enabled_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="User who last changed the enabled status (null if system-set)",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["enabled_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        # Unique constraint: one entry per module per tenant
        sa.UniqueConstraint("tenant_id", "module_name", name="uq_tenant_modules_tenant_module"),
        comment="Module enable/disable configuration per tenant",
    )

    # Create indexes
    op.create_index("ix_tenant_modules_tenant_id", "tenant_modules", ["tenant_id"])
    op.create_index("ix_tenant_modules_module_name", "tenant_modules", ["module_name"])
    op.create_index("ix_tenant_modules_enabled", "tenant_modules", ["enabled"])


def downgrade() -> None:
    """Drop tenant_modules table."""
    if not table_exists("tenant_modules"):
        return

    # Drop indexes
    op.drop_index("ix_tenant_modules_enabled", table_name="tenant_modules")
    op.drop_index("ix_tenant_modules_module_name", table_name="tenant_modules")
    op.drop_index("ix_tenant_modules_tenant_id", table_name="tenant_modules")
    # Drop table
    op.drop_table("tenant_modules")
