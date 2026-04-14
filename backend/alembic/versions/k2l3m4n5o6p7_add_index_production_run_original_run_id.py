"""Add index on production_runs.original_run_id for reprint query performance

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-04-14 03:46:00.000000

original_run_id is a self-referencing FK used to track reprints.  Without an
index, queries that look up "all reprints of run X" require a full table scan.
"""

from alembic import op

revision = "k2l3m4n5o6p7"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None

_INDEX = "ix_production_runs_original_run_id"
_TABLE = "production_runs"
_COLUMN = "original_run_id"


def upgrade() -> None:
    op.create_index(_INDEX, _TABLE, [_COLUMN])


def downgrade() -> None:
    op.drop_index(_INDEX, table_name=_TABLE)
