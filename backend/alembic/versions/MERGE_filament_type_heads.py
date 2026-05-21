"""Merge all 12 existing heads before filament type data migration.

Revision ID: merge_filament_type_heads
Revises: (all 12 current heads)
Create Date: 2026-05-19

"""

# revision identifiers, used by Alembic.
revision = "merge_filament_type_heads"
down_revision = (
    "8e9eb6466afa",
    "a0b1c2d3e4f5",
    "b1c2d3e4f5g6",
    "c384baaa92e4",
    "c6d7e8f9a0b1",
    "c6d7e8f9g0h1",
    "j4k5l6m7n8o9",
    "k2l3m4n5o6p7",
    "l9m0n1o2p3q4",
    "o2p3q4r5s6t7",
    "r5s6t7u8v9w0",
    "u8v9w0x1y2z3",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge all 12 heads — no schema changes."""
    pass


def downgrade() -> None:
    """Merge point — no schema changes to revert."""
    pass
