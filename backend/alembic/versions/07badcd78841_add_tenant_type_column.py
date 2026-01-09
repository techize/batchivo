"""add_tenant_type_column

Revision ID: 07badcd78841
Revises: 8c3c671816d9
Create Date: 2025-12-30 13:45:00.000000

This migration adds the tenant_type column to the tenants table.
Tenant type determines which features, modules, and terminology are
available to a tenant (3D printing, hand knitting, machine knitting, generic).

Existing tenants default to 'three_d_print' since nozzly was originally
built for 3D printing businesses.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "07badcd78841"
down_revision: Union[str, Sequence[str], None] = "8c3c671816d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tenant_type column to tenants table."""
    # Add tenant_type column with default value for existing tenants
    op.add_column(
        "tenants",
        sa.Column(
            "tenant_type",
            sa.String(50),
            nullable=False,
            server_default="three_d_print",
            comment="Tenant business type (three_d_print, hand_knitting, machine_knitting, generic)",
        ),
    )

    # Create index for tenant_type (useful for querying tenants by type)
    op.create_index(
        "ix_tenants_tenant_type",
        "tenants",
        ["tenant_type"],
    )


def downgrade() -> None:
    """Remove tenant_type column from tenants table."""
    op.drop_index("ix_tenants_tenant_type", table_name="tenants")
    op.drop_column("tenants", "tenant_type")
