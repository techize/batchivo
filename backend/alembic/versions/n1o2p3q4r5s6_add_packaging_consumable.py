"""Add packaging consumable to products

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2024-12-07

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "n1o2p3q4r5s6"
down_revision: Union[str, None] = "m0n1o2p3q4r5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add packaging_consumable_id column (FK to consumable_types)
    op.add_column(
        "products",
        sa.Column(
            "packaging_consumable_id",
            sa.UUID(),
            sa.ForeignKey("consumable_types.id", ondelete="SET NULL"),
            nullable=True,
            comment="Optional consumable used for packaging (e.g., box)",
        ),
    )

    # Add packaging_quantity column
    op.add_column(
        "products",
        sa.Column(
            "packaging_quantity",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Quantity of packaging consumable per product",
        ),
    )

    # Create index on packaging_consumable_id
    op.create_index("ix_products_packaging_consumable_id", "products", ["packaging_consumable_id"])


def downgrade() -> None:
    op.drop_index("ix_products_packaging_consumable_id", "products")
    op.drop_column("products", "packaging_quantity")
    op.drop_column("products", "packaging_consumable_id")
