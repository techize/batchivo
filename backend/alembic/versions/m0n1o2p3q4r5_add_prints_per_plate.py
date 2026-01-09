"""Add prints_per_plate to models table

Revision ID: m0n1o2p3q4r5
Revises: l9m0n1o2p3q4
Create Date: 2024-12-07

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "m0n1o2p3q4r5"
down_revision: Union[str, None] = "l9m0n1o2p3q4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add prints_per_plate column with default value of 1
    op.add_column(
        "models",
        sa.Column(
            "prints_per_plate",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Number of items per plate (material weight and print time are divided by this)",
        ),
    )


def downgrade() -> None:
    op.drop_column("models", "prints_per_plate")
