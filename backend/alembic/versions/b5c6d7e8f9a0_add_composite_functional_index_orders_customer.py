"""Add composite functional index on orders (tenant_id, lower(customer_email)).

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-03-22 17:30:00.000000

The customer account order-history query filters by:
    WHERE tenant_id = :tenant AND LOWER(customer_email) = LOWER(:email)

The existing ix_orders_customer_email index is a plain btree on customer_email;
Postgres cannot use it when the query applies lower() to the column.

This migration:
  1. Drops the plain ix_orders_customer_email index.
  2. Creates a composite functional index on (tenant_id, lower(customer_email))
     so the common pattern uses a single efficient index scan.
"""

from alembic import op


# revision identifiers
revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old plain index (replaced by the functional composite below)
    # Use IF EXISTS — the index may not exist if the DB was set up without it
    op.execute("DROP INDEX IF EXISTS ix_orders_customer_email")

    # Composite functional index: tenant isolation + case-insensitive email lookup
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_orders_tenant_lower_email
        ON orders (tenant_id, lower(customer_email))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_orders_tenant_lower_email")

    # Restore the original plain index
    op.create_index(
        "ix_orders_customer_email",
        "orders",
        ["customer_email"],
    )
