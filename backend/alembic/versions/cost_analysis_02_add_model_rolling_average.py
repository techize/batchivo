"""Add model rolling average production cost fields

Revision ID: cost_analysis_02
Revises: d59377f9563e
Create Date: 2026-01-19 15:00:00.000000

Phase 2 of production cost tracking:
- Model: actual_production_cost (rolling average from completed runs)
- Model: production_cost_count (number of runs in average)
- Model: production_cost_updated_at (last update timestamp)

Enables comparison of BOM-based theoretical cost vs actual production cost.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cost_analysis_02"
down_revision: Union[str, Sequence[str], None] = "d59377f9563e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add model production cost tracking columns."""
    op.add_column(
        "models",
        sa.Column(
            "actual_production_cost",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="Rolling average actual production cost per unit from completed runs",
        ),
    )
    op.add_column(
        "models",
        sa.Column(
            "production_cost_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of completed production runs included in rolling average",
        ),
    )
    op.add_column(
        "models",
        sa.Column(
            "production_cost_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time actual_production_cost was updated",
        ),
    )


def downgrade() -> None:
    """Remove model production cost tracking columns."""
    op.drop_column("models", "production_cost_updated_at")
    op.drop_column("models", "production_cost_count")
    op.drop_column("models", "actual_production_cost")
