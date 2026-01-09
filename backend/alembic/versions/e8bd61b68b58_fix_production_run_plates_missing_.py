"""fix_production_run_plates_missing_columns

Revision ID: e8bd61b68b58
Revises: 03fcf3292f37
Create Date: 2025-12-16 16:29:52.746800

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8bd61b68b58"
down_revision: Union[str, Sequence[str], None] = "03fcf3292f37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fix production_run_plates table missing columns
    # These columns were added to the model but migrations were modified after being applied

    # Add prints_per_plate column
    op.add_column(
        "production_run_plates",
        sa.Column(
            "prints_per_plate",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="How many items per single plate",
        ),
    )

    # Add estimated_material_weight_grams column
    op.add_column(
        "production_run_plates",
        sa.Column(
            "estimated_material_weight_grams",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Estimated material weight per plate",
        ),
    )

    # Add started_at column
    op.add_column(
        "production_run_plates",
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When plate printing started",
        ),
    )

    # Add completed_at column
    op.add_column(
        "production_run_plates",
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When plate printing completed",
        ),
    )

    # Add actual_print_time_minutes column
    op.add_column(
        "production_run_plates",
        sa.Column(
            "actual_print_time_minutes", sa.Integer(), nullable=True, comment="Actual print time"
        ),
    )

    # Add actual_material_weight_grams column
    op.add_column(
        "production_run_plates",
        sa.Column(
            "actual_material_weight_grams",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Actual material used",
        ),
    )

    # Add successful_prints column
    op.add_column(
        "production_run_plates",
        sa.Column(
            "successful_prints",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of successful prints from this plate",
        ),
    )

    # Add failed_prints column
    op.add_column(
        "production_run_plates",
        sa.Column(
            "failed_prints",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of failed prints from this plate",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove added columns in reverse order
    op.drop_column("production_run_plates", "failed_prints")
    op.drop_column("production_run_plates", "successful_prints")
    op.drop_column("production_run_plates", "actual_material_weight_grams")
    op.drop_column("production_run_plates", "actual_print_time_minutes")
    op.drop_column("production_run_plates", "completed_at")
    op.drop_column("production_run_plates", "started_at")
    op.drop_column("production_run_plates", "estimated_material_weight_grams")
    op.drop_column("production_run_plates", "prints_per_plate")
