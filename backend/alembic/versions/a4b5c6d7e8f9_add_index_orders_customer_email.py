"""Add index on orders.customer_email for faster customer account lookups.

Revision ID: a4b5c6d7e8f9
Revises: z3a4b5c6d7e8
Create Date: 2026-03-22 13:00:00.000000

Customer account order history queries filter by customer_email with a
case-insensitive match. Without an index this is a full table scan on
every customer login or order lookup.
"""

from alembic import op


# revision identifiers
revision = "a4b5c6d7e8f9"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_orders_customer_email",
        "orders",
        ["customer_email"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_customer_email", table_name="orders")
