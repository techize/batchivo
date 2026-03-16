"""Add 3D printing fields to product_variants

Revision ID: a0b1c2d3e4f5
Revises: 1d212c2984fe
Create Date: 2026-03-16 12:00:00.000000

Adds fulfilment_type, lead_time_days, material_cost_pence, and print_time_hours
to product_variants to support sized 3D-printed products (e.g. dinosaur range)
with per-size pricing, stock tracking, and print-to-order lead times.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "a0b1c2d3e4f5"
down_revision = "1d212c2984fe"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table_name)"
        ),
        {"table_name": table_name},
    )
    return result.scalar()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists on a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table_name AND column_name = :column_name"
            ")"
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Add 3D printing fields to product_variants."""
    if not table_exists("product_variants"):
        return

    if not column_exists("product_variants", "fulfilment_type"):
        op.add_column(
            "product_variants",
            sa.Column(
                "fulfilment_type",
                sa.String(20),
                nullable=False,
                server_default="stock",
                comment="Fulfilment method: stock or print_to_order",
            ),
        )

    if not column_exists("product_variants", "lead_time_days"):
        op.add_column(
            "product_variants",
            sa.Column(
                "lead_time_days",
                sa.Integer(),
                nullable=True,
                comment="Days from order to dispatch for print-to-order variants",
            ),
        )

    if not column_exists("product_variants", "material_cost_pence"):
        op.add_column(
            "product_variants",
            sa.Column(
                "material_cost_pence",
                sa.Integer(),
                nullable=True,
                comment="Cost of filament for this size variant in pence",
            ),
        )

    if not column_exists("product_variants", "print_time_hours"):
        op.add_column(
            "product_variants",
            sa.Column(
                "print_time_hours",
                sa.Numeric(6, 2),
                nullable=True,
                comment="Estimated print time for this size in hours",
            ),
        )


def downgrade() -> None:
    """Remove 3D printing fields from product_variants."""
    if not table_exists("product_variants"):
        return

    for col in ("print_time_hours", "material_cost_pence", "lead_time_days", "fulfilment_type"):
        if column_exists("product_variants", col):
            op.drop_column("product_variants", col)
