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


def upgrade() -> None:
    # Add customer_id column to orders (optional FK to customers)
    op.add_column(
        "orders",
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Reference to customer account if logged in",
        ),
    )
    op.create_foreign_key(
        "fk_orders_customer_id",
        "orders",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    # Add discount columns to orders
    op.add_column(
        "orders",
        sa.Column(
            "discount_code",
            sa.String(50),
            nullable=True,
            comment="Applied discount code",
        ),
    )
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
