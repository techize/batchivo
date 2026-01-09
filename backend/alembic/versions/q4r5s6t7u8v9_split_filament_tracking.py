"""Split filament tracking into model, flushed, and tower weights.

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2024-12-09 19:50:00.000000

This migration splits the filament tracking fields to separately track:
- Model weight: filament used for actual models
- Flushed weight: filament flushed during color changes
- Tower weight: purge tower material

Both at the ProductionRun level (estimates) and ProductionRunMaterial level (per-spool).
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "q4r5s6t7u8v9"
down_revision = "p3q4r5s6t7u8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================
    # Production Runs - split estimated fields
    # ========================================

    # Rename existing columns for clarity
    # estimated_total_filament_grams -> estimated_model_weight_grams
    op.alter_column(
        "production_runs",
        "estimated_total_filament_grams",
        new_column_name="estimated_model_weight_grams",
    )

    # estimated_total_purge_grams -> estimated_flushed_grams (purge/flush)
    op.alter_column(
        "production_runs", "estimated_total_purge_grams", new_column_name="estimated_flushed_grams"
    )

    # Add new column for tower weight
    op.add_column(
        "production_runs", sa.Column("estimated_tower_grams", sa.Numeric(10, 2), nullable=True)
    )

    # Add computed total column (stored for query performance)
    op.add_column(
        "production_runs",
        sa.Column("estimated_total_weight_grams", sa.Numeric(10, 2), nullable=True),
    )

    # Split actual usage fields similarly
    op.alter_column(
        "production_runs",
        "actual_total_filament_grams",
        new_column_name="actual_model_weight_grams",
    )

    op.alter_column(
        "production_runs", "actual_total_purge_grams", new_column_name="actual_flushed_grams"
    )

    op.add_column(
        "production_runs", sa.Column("actual_tower_grams", sa.Numeric(10, 2), nullable=True)
    )

    op.add_column(
        "production_runs", sa.Column("actual_total_weight_grams", sa.Numeric(10, 2), nullable=True)
    )

    # ========================================
    # Production Run Materials - split per-spool fields
    # ========================================

    # Rename existing columns
    # estimated_weight_grams -> estimated_model_weight_grams
    op.alter_column(
        "production_run_materials",
        "estimated_weight_grams",
        new_column_name="estimated_model_weight_grams",
    )

    # estimated_purge_grams -> estimated_flushed_grams
    op.alter_column(
        "production_run_materials",
        "estimated_purge_grams",
        new_column_name="estimated_flushed_grams",
    )

    # Add new column for tower weight per spool
    op.add_column(
        "production_run_materials",
        sa.Column("estimated_tower_grams", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )

    # Split actual usage fields
    op.alter_column(
        "production_run_materials",
        "actual_weight_manual",
        new_column_name="actual_model_weight_grams",
    )

    op.alter_column(
        "production_run_materials", "actual_purge_grams", new_column_name="actual_flushed_grams"
    )

    op.add_column(
        "production_run_materials",
        sa.Column("actual_tower_grams", sa.Numeric(10, 2), nullable=True),
    )

    # Remove server default after column is created
    op.alter_column("production_run_materials", "estimated_tower_grams", server_default=None)


def downgrade() -> None:
    # ========================================
    # Production Run Materials - revert
    # ========================================
    op.drop_column("production_run_materials", "actual_tower_grams")

    op.alter_column(
        "production_run_materials", "actual_flushed_grams", new_column_name="actual_purge_grams"
    )

    op.alter_column(
        "production_run_materials",
        "actual_model_weight_grams",
        new_column_name="actual_weight_manual",
    )

    op.drop_column("production_run_materials", "estimated_tower_grams")

    op.alter_column(
        "production_run_materials",
        "estimated_flushed_grams",
        new_column_name="estimated_purge_grams",
    )

    op.alter_column(
        "production_run_materials",
        "estimated_model_weight_grams",
        new_column_name="estimated_weight_grams",
    )

    # ========================================
    # Production Runs - revert
    # ========================================
    op.drop_column("production_runs", "actual_total_weight_grams")
    op.drop_column("production_runs", "actual_tower_grams")

    op.alter_column(
        "production_runs", "actual_flushed_grams", new_column_name="actual_total_purge_grams"
    )

    op.alter_column(
        "production_runs",
        "actual_model_weight_grams",
        new_column_name="actual_total_filament_grams",
    )

    op.drop_column("production_runs", "estimated_total_weight_grams")
    op.drop_column("production_runs", "estimated_tower_grams")

    op.alter_column(
        "production_runs", "estimated_flushed_grams", new_column_name="estimated_total_purge_grams"
    )

    op.alter_column(
        "production_runs",
        "estimated_model_weight_grams",
        new_column_name="estimated_total_filament_grams",
    )
