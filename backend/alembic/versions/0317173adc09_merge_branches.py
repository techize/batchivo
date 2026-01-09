"""merge_branches

Revision ID: 0317173adc09
Revises: dc468d7bd2df, j4k5l6m7n8o9
Create Date: 2026-01-04 11:46:44.065090

Merges:
- dc468d7bd2df (platform admin and print queue branch)
- j4k5l6m7n8o9 (model files branch, includes h2i3j4k5l6m7 and i3j4k5l6m7n8)
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "0317173adc09"
down_revision: Union[str, Sequence[str], None] = ("dc468d7bd2df", "j4k5l6m7n8o9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
