"""merge_model_files_branch

Revision ID: 8a963ea7f73a
Revises: 0317173adc09
Create Date: 2026-01-04 20:10:02.517124

Note: No longer a merge point - 0317173adc09 now includes all branches.
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "8a963ea7f73a"
down_revision: Union[str, Sequence[str], None] = "0317173adc09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
