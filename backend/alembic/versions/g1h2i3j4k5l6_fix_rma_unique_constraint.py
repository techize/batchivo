"""Fix RMA number unique constraint to be per-tenant

Revision ID: g1h2i3j4k5l6
Revises: f0g1h2i3j4k5
Create Date: 2026-01-01 19:50:00.000000

Changes global unique constraint on rma_number to per-tenant unique constraint.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "g1h2i3j4k5l6"
down_revision = "f0g1h2i3j4k5"
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
    """Change RMA number unique constraint to per-tenant."""
    # Drop the global unique constraint/index if it exists
    if constraint_exists("return_requests_rma_number_key"):
        op.drop_constraint("return_requests_rma_number_key", "return_requests", type_="unique")

    # Create per-tenant unique constraint if it doesn't exist
    if not constraint_exists("uq_return_request_tenant_rma"):
        op.create_unique_constraint(
            "uq_return_request_tenant_rma",
            "return_requests",
            ["tenant_id", "rma_number"],
        )


def downgrade() -> None:
    """Restore global unique constraint (may fail if duplicates exist)."""
    if constraint_exists("uq_return_request_tenant_rma"):
        op.drop_constraint("uq_return_request_tenant_rma", "return_requests", type_="unique")
    if not constraint_exists("return_requests_rma_number_key"):
        op.create_unique_constraint(
            "return_requests_rma_number_key",
            "return_requests",
            ["rma_number"],
        )
