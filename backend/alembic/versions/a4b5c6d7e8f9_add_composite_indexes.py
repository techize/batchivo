"""Add composite indexes for common query patterns.

Revision ID: a4b5c6d7e8f9
Revises: z3a4b5c6d7e8
Create Date: 2026-03-23 09:00:00.000000

Adds composite indexes to eliminate full table scans on frequently-combined filter
conditions. The orders list endpoint always filters by tenant_id and optionally by
status; the current individual indexes force PostgreSQL to pick one and scan for the
other. A composite index covers both conditions in a single pass.

Also adds (tenant_id, created_at) to support the default sort on the orders list.
"""

from alembic import op


# revision identifiers
revision = "a4b5c6d7e8f9"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index for orders filtered by tenant + status (orders list endpoint)
    op.create_index(
        "idx_orders_tenant_status",
        "orders",
        ["tenant_id", "status"],
    )
    # Composite index for orders filtered by tenant + sorted by created_at (default sort)
    op.create_index(
        "idx_orders_tenant_created_at",
        "orders",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_orders_tenant_created_at", table_name="orders")
    op.drop_index("idx_orders_tenant_status", table_name="orders")
