"""Add production run cost analysis fields

Revision ID: cost_analysis_01
Revises: add_is_dragon_01
Create Date: 2026-01-06 15:00:00.000000

Adds fields for tracking actual production costs per item/plate:
- ProductionRun: cost_per_gram_actual, successful_weight_grams
- ProductionRunItem: model_weight_grams, actual_cost_per_unit
- ProductionRunPlate: model_weight_grams, actual_cost_per_unit

Enables cost analysis: actual_cost = total_material_cost / successful_weight
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cost_analysis_01"
down_revision: Union[str, Sequence[str], None] = "add_is_dragon_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cost analysis columns."""
    # ProductionRun columns
    op.add_column(
        "production_runs",
        sa.Column(
            "cost_per_gram_actual",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
            comment="Actual cost per gram = total_material_cost / successful_weight",
        ),
    )
    op.add_column(
        "production_runs",
        sa.Column(
            "successful_weight_grams",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment="Total theoretical weight of successful items (for cost calculation)",
        ),
    )

    # ProductionRunItem columns
    op.add_column(
        "production_run_items",
        sa.Column(
            "model_weight_grams",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment="Cached model weight from BOM (for cost calculation)",
        ),
    )
    op.add_column(
        "production_run_items",
        sa.Column(
            "actual_cost_per_unit",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="Actual cost per unit = model_weight × cost_per_gram_actual",
        ),
    )

    # ProductionRunPlate columns
    op.add_column(
        "production_run_plates",
        sa.Column(
            "model_weight_grams",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment="Cached model weight from BOM (for cost calculation)",
        ),
    )
    op.add_column(
        "production_run_plates",
        sa.Column(
            "actual_cost_per_unit",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="Actual cost per unit = model_weight × cost_per_gram_actual",
        ),
    )


def downgrade() -> None:
    """Remove cost analysis columns."""
    # ProductionRunPlate columns
    op.drop_column("production_run_plates", "actual_cost_per_unit")
    op.drop_column("production_run_plates", "model_weight_grams")

    # ProductionRunItem columns
    op.drop_column("production_run_items", "actual_cost_per_unit")
    op.drop_column("production_run_items", "model_weight_grams")

    # ProductionRun columns
    op.drop_column("production_runs", "successful_weight_grams")
    op.drop_column("production_runs", "cost_per_gram_actual")
