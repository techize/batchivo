"""update_production_runs_printer_product

Revision ID: e8b435cc2b4a
Revises: c7503ada4f0b
Create Date: 2025-12-15 13:29:38.448436

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8b435cc2b4a"
down_revision: Union[str, Sequence[str], None] = "c7503ada4f0b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add printer_id column
    op.add_column(
        "production_runs",
        sa.Column(
            "printer_id", sa.UUID(), nullable=True, comment="Primary printer used for this run"
        ),
    )
    op.create_foreign_key(
        "fk_production_runs_printer",
        "production_runs",
        "printers",
        ["printer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_production_runs_printer", "production_runs", ["printer_id"])

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
    op.create_foreign_key(
        "fk_production_runs_product",
        "production_runs",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_production_runs_product", "production_runs", ["product_id"])

    # Add plate tracking columns
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
    # Drop plate tracking columns
    op.drop_column("production_runs", "completed_plates")
    op.drop_column("production_runs", "total_plates")

    # Drop product_id
    op.drop_index("idx_production_runs_product", table_name="production_runs")
    op.drop_constraint("fk_production_runs_product", "production_runs", type_="foreignkey")
    op.drop_column("production_runs", "product_id")

    # Drop printer_id
    op.drop_index("idx_production_runs_printer", table_name="production_runs")
    op.drop_constraint("fk_production_runs_printer", "production_runs", type_="foreignkey")
    op.drop_column("production_runs", "printer_id")
