"""add_model_printer_configs_table

Revision ID: c7503ada4f0b
Revises: 43cc1df327c1
Create Date: 2025-12-15 13:29:03.748883

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7503ada4f0b"
down_revision: Union[str, Sequence[str], None] = "43cc1df327c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create model_printer_configs table
    op.create_table(
        "model_printer_configs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("model_id", sa.UUID(), nullable=False),
        sa.Column("printer_id", sa.UUID(), nullable=False),
        sa.Column(
            "prints_per_plate",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="How many of this model fit on one plate for this printer",
        ),
        sa.Column(
            "print_time_minutes",
            sa.Integer(),
            nullable=True,
            comment="Total print time for full plate (all prints_per_plate items)",
        ),
        sa.Column(
            "material_weight_grams",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment="Material weight for ONE item (not full plate)",
        ),
        sa.Column(
            "bed_temperature",
            sa.Integer(),
            nullable=True,
            comment="Bed temperature for this model on this printer",
        ),
        sa.Column(
            "nozzle_temperature",
            sa.Integer(),
            nullable=True,
            comment="Nozzle temperature for this model on this printer",
        ),
        sa.Column(
            "layer_height",
            sa.Numeric(precision=3, scale=2),
            nullable=True,
            comment="Layer height in millimeters",
        ),
        sa.Column(
            "infill_percentage", sa.Integer(), nullable=True, comment="Infill percentage (0-100)"
        ),
        sa.Column(
            "supports",
            sa.Boolean(),
            nullable=True,
            server_default="false",
            comment="Whether supports are required",
        ),
        sa.Column(
            "brim",
            sa.Boolean(),
            nullable=True,
            server_default="false",
            comment="Whether brim is required",
        ),
        sa.Column(
            "slicer_settings",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
            comment="Additional slicer settings (speed, retraction, etc.)",
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
        sa.ForeignKeyConstraint(["model_id"], ["models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["printer_id"], ["printers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", "printer_id", name="uq_model_printer"),
        sa.CheckConstraint("prints_per_plate > 0", name="check_prints_per_plate_positive"),
        comment="Printer-specific configuration for each model (prints per plate, times, settings)",
    )

    # Create indexes
    op.create_index("idx_model_printer_configs_model", "model_printer_configs", ["model_id"])
    op.create_index("idx_model_printer_configs_printer", "model_printer_configs", ["printer_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_model_printer_configs_printer", table_name="model_printer_configs")
    op.drop_index("idx_model_printer_configs_model", table_name="model_printer_configs")

    # Drop table
    op.drop_table("model_printer_configs")
