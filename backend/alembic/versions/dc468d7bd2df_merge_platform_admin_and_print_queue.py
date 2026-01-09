"""merge_platform_admin_and_print_queue

Revision ID: dc468d7bd2df
Revises: a4b5c6d7e8f9, c6d7e8f9g0h1
Create Date: 2025-12-31 12:29:54.266831

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "dc468d7bd2df"
down_revision: Union[str, Sequence[str], None] = ("a4b5c6d7e8f9", "c6d7e8f9g0h1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
