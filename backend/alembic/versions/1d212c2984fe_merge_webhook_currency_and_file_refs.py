"""merge_webhook_currency_and_file_refs

Revision ID: 1d212c2984fe
Revises: 8e9eb6466afa, c384baaa92e4, local_file_refs_01
Create Date: 2026-01-31 14:01:54.716173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d212c2984fe'
down_revision: Union[str, Sequence[str], None] = ('8e9eb6466afa', 'c384baaa92e4', 'local_file_refs_01')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
