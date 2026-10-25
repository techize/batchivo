"""Add missing discount and customer columns to orders

Revision ID: h8i9j0k1l2m3
Revises: 7399942463dd
Create Date: 2025-12-30 17:05:00.000000

Adds discount_code, discount_amount, and customer_id columns to orders table
that were missing from the discount_codes migration.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "7399942463dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table AND column_name = :column
            )
        """),
        {"table": table_name, "column": column_name},
    )
    return result.scalar()


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = :name
            )
        """),
        {"name": index_name},
    )
    return result.scalar()


def constraint_exists(constraint_name: str) -> bool:
    """Check if a constraint exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = :name
            )
        """),
        {"name": constraint_name},
    )
    return result.scalar()


def upgrade() -> None:
    # This migration is idempotent - it checks if columns/constraints/indexes
    # exist before adding them, since this branch may merge with another
    # that already added some of these.

    # Add customer_id column to orders (optional FK to customers)
    if not column_exists("orders", "customer_id"):
        op.add_column(
            "orders",
            sa.Column(
                "customer_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                comment="Reference to customer account if logged in",
            ),
        )
    if not constraint_exists("fk_orders_customer_id"):
        op.create_foreign_key(
            "fk_orders_customer_id",
            "orders",
            "customers",
            ["customer_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if not index_exists("ix_orders_customer_id"):
        op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    # Add discount columns to orders
    if not column_exists("orders", "discount_code"):
        op.add_column(
            "orders",
            sa.Column(
                "discount_code",
                sa.String(50),
                nullable=True,
                comment="Applied discount code",
            ),
        )
    if not column_exists("orders", "discount_amount"):
        op.add_column(
            "orders",
            sa.Column(
                "discount_amount",
                sa.Numeric(10, 2),
                server_default="0.00",
                nullable=False,
                comment="Discount amount applied",
            ),
        )


def downgrade() -> None:
    op.drop_column("orders", "discount_amount")
    op.drop_column("orders", "discount_code")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_constraint("fk_orders_customer_id", "orders", type_="foreignkey")
    op.drop_column("orders", "customer_id")
