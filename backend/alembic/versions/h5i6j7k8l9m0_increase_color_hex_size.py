"""increase_color_hex_size

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2025-12-04 21:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "h5i6j7k8l9m0"
down_revision: Union[str, Sequence[str], None] = "g4h5i6j7k8l9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Increase color_hex column size to accommodate RGBA hex codes (8 chars)."""
    op.alter_column(
        "spoolmandb_filaments",
        "color_hex",
        type_=sa.String(9),  # 8 chars for RGBA + 1 for safety
        existing_type=sa.String(7),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert color_hex column size."""
    op.alter_column(
        "spoolmandb_filaments",
        "color_hex",
        type_=sa.String(7),
        existing_type=sa.String(9),
        existing_nullable=True,
    )
