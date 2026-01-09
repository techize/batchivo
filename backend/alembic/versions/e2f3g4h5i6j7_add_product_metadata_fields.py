"""add_product_metadata_fields

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2025-11-18 20:08:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e2f3g4h5i6j7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3g4h5i6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add product metadata fields for CSV import support."""
    # Add designer field
    op.add_column(
        "products",
        sa.Column(
            "designer",
            sa.String(length=200),
            nullable=True,
            comment='Model designer name (e.g., "Cinderwings")',
        ),
    )

    # Add source field
    op.add_column(
        "products",
        sa.Column(
            "source",
            sa.String(length=200),
            nullable=True,
            comment='Model source platform (e.g., "Thangs", "Thingiverse")',
        ),
    )

    # Add print_time_minutes field
    op.add_column(
        "products",
        sa.Column(
            "print_time_minutes",
            sa.Integer(),
            nullable=True,
            comment="Estimated print time in minutes",
        ),
    )

    # Add machine field
    op.add_column(
        "products",
        sa.Column(
            "machine",
            sa.String(length=100),
            nullable=True,
            comment='Printer/machine used (e.g., "A1", "P1S")',
        ),
    )

    # Add last_printed_date field
    op.add_column(
        "products",
        sa.Column(
            "last_printed_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time this product was printed",
        ),
    )

    # Add units_in_stock field
    op.add_column(
        "products",
        sa.Column(
            "units_in_stock",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="Number of finished units in inventory",
        ),
    )

    # Create index on machine for filtering
    op.create_index("ix_products_machine", "products", ["machine"])


def downgrade() -> None:
    """Remove product metadata fields."""
    # Drop index first
    op.drop_index("ix_products_machine", table_name="products")

    # Drop columns in reverse order
    op.drop_column("products", "units_in_stock")
    op.drop_column("products", "last_printed_date")
    op.drop_column("products", "machine")
    op.drop_column("products", "print_time_minutes")
    op.drop_column("products", "source")
    op.drop_column("products", "designer")
