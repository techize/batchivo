"""Convert tenants.settings from JSON to JSONB.

Revision ID: a1b2c3d4e5f6
Revises: z3a4b5c6d7e8
Create Date: 2026-03-17 22:30:00.000000

JSONB is required for jsonb_extract_path_text() queries used in
resolve_tenant_by_custom_domain.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = "a1b2c3d4e5f6"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "tenants",
        "settings",
        existing_type=sa.JSON(),
        type_=JSONB(),
        postgresql_using="settings::jsonb",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "tenants",
        "settings",
        existing_type=JSONB(),
        type_=sa.JSON(),
        postgresql_using="settings::json",
        existing_nullable=False,
    )
