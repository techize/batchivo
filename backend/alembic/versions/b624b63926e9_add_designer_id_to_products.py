"""add_designer_id_to_products

Revision ID: b624b63926e9
Revises: 79f717599971
Create Date: 2025-12-16 15:14:20.462541

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b624b63926e9"
down_revision: Union[str, Sequence[str], None] = "79f717599971"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column(
            "designer_id",
            sa.Uuid(),
            nullable=True,
            comment="Designer who created this product's 3D model(s)",
        ),
    )
    op.create_index(op.f("ix_products_designer_id"), "products", ["designer_id"], unique=False)
    op.create_foreign_key(
        "fk_products_designer_id",
        "products",
        "designers",
        ["designer_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_products_designer_id", "products", type_="foreignkey")
    op.drop_index(op.f("ix_products_designer_id"), table_name="products")
    op.drop_column("products", "designer_id")
