"""Add print_to_order field to products

Revision ID: v9w0x1y2z3a4
Revises: u8v9w0x1y2z3
Create Date: 2025-12-24 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "v9w0x1y2z3a4"
down_revision: Union[str, Sequence[str], None] = "u8v9w0x1y2z3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column(
            "print_to_order",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether product is printed to order (vs in-stock ready to ship)",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("products", "print_to_order")
