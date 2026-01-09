"""Add free_shipping to products

Revision ID: x1y2z3a4b5c6
Revises: w0x1y2z3a4b5
Create Date: 2025-12-29 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "x1y2z3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "w0x1y2z3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column(
            "free_shipping",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether product qualifies for free shipping",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("products", "free_shipping")
