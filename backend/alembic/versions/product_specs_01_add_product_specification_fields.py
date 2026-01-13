"""Add product specification fields

Revision ID: product_specs_01
Revises: cost_analysis_01
Create Date: 2026-01-13 08:50:00.000000

Adds product specification fields for Etsy sync and display:
- weight_grams: Product weight (auto-captured from production or manual)
- size_cm: Product size/length (manual entry)
- print_time_hours: Print time (auto-captured from production or manual)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "product_specs_01"
down_revision: Union[str, None] = "cost_analysis_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add product specification fields
    op.add_column(
        "products",
        sa.Column(
            "weight_grams",
            sa.Integer(),
            nullable=True,
            comment="Product weight in grams (auto-captured from production run or manual)",
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "size_cm",
            sa.Numeric(precision=6, scale=1),
            nullable=True,
            comment="Product size/length in centimeters (manual entry)",
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "print_time_hours",
            sa.Numeric(precision=6, scale=2),
            nullable=True,
            comment="Print time in hours (auto-captured from production run or manual)",
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "print_time_hours")
    op.drop_column("products", "size_cm")
    op.drop_column("products", "weight_grams")
