"""add_empty_spool_weight

Revision ID: f3g4h5i6j7k8
Revises: e2f3g4h5i6j7
Create Date: 2025-12-04 20:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3g4h5i6j7k8"
down_revision: Union[str, Sequence[str], None] = "e2f3g4h5i6j7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add empty_spool_weight field to spools table."""
    op.add_column(
        "spools",
        sa.Column(
            "empty_spool_weight",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment="Weight of empty spool in grams (for gross weight calculations)",
        ),
    )


def downgrade() -> None:
    """Remove empty_spool_weight field from spools table."""
    op.drop_column("spools", "empty_spool_weight")
