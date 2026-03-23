"""Add composite indexes for printer_connection and inventory_transaction.

Revision ID: f2e3d4c5b6a7
Revises: e1d9c135aa30
Create Date: 2026-03-23 13:10:00.000000

Adds composite indexes for common query patterns:
- printer_connections(tenant_id, connection_type): listing connections by tenant+type
  avoids full table scan when filtering active Bambu/OctoPrint/Klipper connections
- inventory_transactions(tenant_id, spool_id, transaction_at): audit trail queries
  avoids full table scan for spool history sorted by date
"""

from alembic import op


# revision identifiers
revision = "f2e3d4c5b6a7"
down_revision = "e1d9c135aa30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_printer_connections_tenant_connection_type",
        "printer_connections",
        ["tenant_id", "connection_type"],
    )

    op.create_index(
        "ix_inventory_transactions_tenant_spool_at",
        "inventory_transactions",
        ["tenant_id", "spool_id", "transaction_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_transactions_tenant_spool_at",
        table_name="inventory_transactions",
    )
    op.drop_index(
        "ix_printer_connections_tenant_connection_type",
        table_name="printer_connections",
    )
