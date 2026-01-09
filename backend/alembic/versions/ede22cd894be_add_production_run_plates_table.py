"""add_production_run_plates_table

Revision ID: ede22cd894be
Revises: e8b435cc2b4a
Create Date: 2025-12-15 13:30:13.599091

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ede22cd894be"
down_revision: Union[str, Sequence[str], None] = "e8b435cc2b4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create production_run_plates table
    op.create_table(
        "production_run_plates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("production_run_id", sa.UUID(), nullable=False),
        sa.Column(
            "plate_number",
            sa.Integer(),
            nullable=False,
            comment="Plate number for ordering (1, 2, 3...)",
        ),
        sa.Column(
            "plate_name",
            sa.String(length=200),
            nullable=False,
            comment='Plate name (e.g., "Dragon Bodies (A1 Mini)")',
        ),
        sa.Column(
            "model_id", sa.UUID(), nullable=False, comment="Model being printed on this plate"
        ),
        sa.Column("printer_id", sa.UUID(), nullable=False, comment="Printer for this plate"),
        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="How many times this plate needs to be printed",
        ),
        sa.Column(
            "prints_per_plate",
            sa.Integer(),
            nullable=False,
            comment="How many items per single plate (e.g., 3 dragons per plate)",
        ),
        sa.Column(
            "print_time_minutes",
            sa.Integer(),
            nullable=True,
            comment="Estimated print time per plate",
        ),
        sa.Column(
            "estimated_material_weight_grams",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment="Estimated material weight per plate",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
            comment="Plate status (pending, printing, complete, failed, cancelled)",
        ),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When plate printing started",
        ),
        sa.Column(
            "completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When plate printing completed",
        ),
        sa.Column(
            "actual_print_time_minutes", sa.Integer(), nullable=True, comment="Actual print time"
        ),
        sa.Column(
            "actual_material_weight_grams",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment="Actual material used",
        ),
        sa.Column(
            "successful_prints",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of successful prints from this plate",
        ),
        sa.Column(
            "failed_prints",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of failed prints from this plate",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["printer_id"], ["printers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("plate_number > 0", name="check_plate_number_positive"),
        sa.CheckConstraint("quantity > 0", name="check_quantity_positive"),
        sa.CheckConstraint(
            "status IN ('pending', 'printing', 'complete', 'failed', 'cancelled')",
            name="check_status_valid",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="check_completed_after_started",
        ),
        comment="Individual print plates within a multi-plate production run",
    )

    # Create indexes
    op.create_index("idx_production_run_plates_run", "production_run_plates", ["production_run_id"])
    op.create_index("idx_production_run_plates_model", "production_run_plates", ["model_id"])
    op.create_index("idx_production_run_plates_printer", "production_run_plates", ["printer_id"])
    op.create_index("idx_production_run_plates_status", "production_run_plates", ["status"])
    op.create_index(
        "idx_production_run_plates_plate_number",
        "production_run_plates",
        ["production_run_id", "plate_number"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_production_run_plates_plate_number", table_name="production_run_plates")
    op.drop_index("idx_production_run_plates_status", table_name="production_run_plates")
    op.drop_index("idx_production_run_plates_printer", table_name="production_run_plates")
    op.drop_index("idx_production_run_plates_model", table_name="production_run_plates")
    op.drop_index("idx_production_run_plates_run", table_name="production_run_plates")

    # Drop table
    op.drop_table("production_run_plates")
