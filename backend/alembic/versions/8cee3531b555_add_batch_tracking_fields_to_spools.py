"""add_batch_tracking_fields_to_spools

Revision ID: 8cee3531b555
Revises: d80bf772b461
Create Date: 2025-11-02 17:57:30.928189

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8cee3531b555"
down_revision: Union[str, Sequence[str], None] = "d80bf772b461"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add batch tracking fields to spools table
    op.add_column(
        "spools",
        sa.Column(
            "purchased_quantity",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Number of spools purchased in this batch",
        ),
    )
    op.add_column(
        "spools",
        sa.Column(
            "spools_remaining",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Number of spools remaining from this batch",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove batch tracking fields
    op.drop_column("spools", "spools_remaining")
    op.drop_column("spools", "purchased_quantity")
