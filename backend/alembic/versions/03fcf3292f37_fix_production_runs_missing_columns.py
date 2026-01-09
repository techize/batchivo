"""fix_production_runs_missing_columns

Revision ID: 03fcf3292f37
Revises: 60aba13508b8
Create Date: 2025-12-16 16:27:07.300841

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "03fcf3292f37"
down_revision: Union[str, Sequence[str], None] = "60aba13508b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Fix production_runs table missing columns
    # These columns were added to the model but the migration was modified
    # after being applied to production.

    # Add printer_id column
    op.add_column(
        "production_runs",
        sa.Column(
            "printer_id", sa.UUID(), nullable=True, comment="Primary printer used for this run"
        ),
    )

    # Add foreign key constraint for printer_id
    op.create_foreign_key(
        "fk_production_runs_printer_id",
        "production_runs",
        "printers",
        ["printer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for printer_id
    op.create_index("idx_production_runs_printer", "production_runs", ["printer_id"], unique=False)

    # Add product_id column
    op.add_column(
        "production_runs",
        sa.Column(
            "product_id",
            sa.UUID(),
            nullable=True,
            comment="Product being produced (if making sellable product)",
        ),
    )

    # Add foreign key constraint for product_id
    op.create_foreign_key(
        "fk_production_runs_product_id",
        "production_runs",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for product_id
    op.create_index("idx_production_runs_product", "production_runs", ["product_id"], unique=False)

    # Add total_plates column
    op.add_column(
        "production_runs",
        sa.Column(
            "total_plates",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Total number of plates in this run",
        ),
    )

    # Add completed_plates column
    op.add_column(
        "production_runs",
        sa.Column(
            "completed_plates",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of plates completed",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove added columns in reverse order
    op.drop_column("production_runs", "completed_plates")
    op.drop_column("production_runs", "total_plates")
    op.drop_index("idx_production_runs_product", table_name="production_runs")
    op.drop_constraint("fk_production_runs_product_id", "production_runs", type_="foreignkey")
    op.drop_column("production_runs", "product_id")
    op.drop_index("idx_production_runs_printer", table_name="production_runs")
    op.drop_constraint("fk_production_runs_printer_id", "production_runs", type_="foreignkey")
    op.drop_column("production_runs", "printer_id")
