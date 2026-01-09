"""Add is_dragon flag to products

Revision ID: add_is_dragon_01
Revises: 8a963ea7f73a
Create Date: 2026-01-05 08:40:00.000000

Adds a dedicated is_dragon boolean field to distinguish dragon products
from general featured products. Previously is_featured was used for both.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_is_dragon_01"
down_revision: Union[str, Sequence[str], None] = "8a963ea7f73a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_dragon column to products table."""
    op.add_column(
        "products",
        sa.Column(
            "is_dragon",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether product appears in the Dragons collection",
        ),
    )
    # Create index for efficient dragon queries
    op.create_index(
        "ix_products_is_dragon",
        "products",
        ["is_dragon"],
    )


def downgrade() -> None:
    """Remove is_dragon column from products table."""
    op.drop_index("ix_products_is_dragon", table_name="products")
    op.drop_column("products", "is_dragon")
