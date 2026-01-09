"""Add unique constraint on discount code per tenant

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-01-01 19:52:00.000000

Adds UniqueConstraint on (tenant_id, code) to prevent duplicate discount codes per tenant.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "h2i3j4k5l6m7"
down_revision = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def constraint_exists(constraint_name: str) -> bool:
    """Check if a constraint exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = :name)"),
        {"name": constraint_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Add unique constraint for discount code per tenant."""
    if not constraint_exists("uq_discount_code_tenant"):
        op.create_unique_constraint(
            "uq_discount_code_tenant",
            "discount_codes",
            ["tenant_id", "code"],
        )


def downgrade() -> None:
    """Remove unique constraint."""
    if constraint_exists("uq_discount_code_tenant"):
        op.drop_constraint("uq_discount_code_tenant", "discount_codes", type_="unique")
