"""Durable legacy-write ownership and final-sync fence.

Revision ID: commerce_handover_v1
Revises: commerce_bridge_v1
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "commerce_handover_v1"
down_revision = "commerce_bridge_v1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commerce_handover",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner", sa.String(20), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "audit", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.CheckConstraint(
            "owner IN ('legacy','fenced','woocommerce')", name="commerce_handover_owner"
        ),
    )
    op.execute(
        "INSERT INTO commerce_handover (tenant_id,owner) VALUES ('ad62b515-17b3-4830-bcb4-3f4c470c26e2','legacy')"
    )
    op.execute("REVOKE ALL ON commerce_handover FROM PUBLIC")


def downgrade():
    raise RuntimeError(
        "Handover history and ownership must survive storefront rollback; do not drop this table"
    )
