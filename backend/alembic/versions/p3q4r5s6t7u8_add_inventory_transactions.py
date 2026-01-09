"""Add inventory_transactions table for audit trail.

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2025-12-09 12:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "p3q4r5s6t7u8"
down_revision: Union[str, None] = "o2p3q4r5s6t7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create inventory_transactions table
    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("spool_id", sa.UUID(), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("weight_before", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("weight_change", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("weight_after", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("production_run_id", sa.UUID(), nullable=True),
        sa.Column("production_run_material_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("transaction_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversal_of_id", sa.UUID(), nullable=True),
        sa.Column("is_reversal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spool_id"], ["spools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["production_run_material_id"], ["production_run_materials.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reversal_of_id"], ["inventory_transactions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Audit trail for all inventory weight changes",
    )

    # Create indexes
    op.create_index("ix_inventory_transactions_tenant_id", "inventory_transactions", ["tenant_id"])
    op.create_index("ix_inventory_transactions_spool_id", "inventory_transactions", ["spool_id"])
    op.create_index(
        "ix_inventory_transactions_transaction_type", "inventory_transactions", ["transaction_type"]
    )
    op.create_index(
        "ix_inventory_transactions_production_run_id",
        "inventory_transactions",
        ["production_run_id"],
    )
    op.create_index(
        "ix_inventory_transactions_production_run_material_id",
        "inventory_transactions",
        ["production_run_material_id"],
    )
    op.create_index("ix_inventory_transactions_user_id", "inventory_transactions", ["user_id"])
    op.create_index(
        "ix_inventory_transactions_reversal_of_id", "inventory_transactions", ["reversal_of_id"]
    )
    op.create_index(
        "ix_inventory_transactions_transaction_at", "inventory_transactions", ["transaction_at"]
    )

    # Composite index for common queries
    op.create_index(
        "ix_inventory_transactions_tenant_spool_date",
        "inventory_transactions",
        ["tenant_id", "spool_id", "transaction_at"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(
        "ix_inventory_transactions_tenant_spool_date", table_name="inventory_transactions"
    )
    op.drop_index("ix_inventory_transactions_transaction_at", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_reversal_of_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_user_id", table_name="inventory_transactions")
    op.drop_index(
        "ix_inventory_transactions_production_run_material_id", table_name="inventory_transactions"
    )
    op.drop_index(
        "ix_inventory_transactions_production_run_id", table_name="inventory_transactions"
    )
    op.drop_index("ix_inventory_transactions_transaction_type", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_spool_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_tenant_id", table_name="inventory_transactions")

    # Drop table
    op.drop_table("inventory_transactions")
