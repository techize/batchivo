"""add_url_fields_to_consumables

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2025-12-05 13:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "k8l9m0n1o2p3"
down_revision: Union[str, Sequence[str], None] = "j7k8l9m0n1o2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add URL fields to consumable tables for purchase links (e.g., Amazon)."""
    # Add supplier_url to consumable_types table
    op.add_column(
        "consumable_types",
        sa.Column(
            "supplier_url",
            sa.String(500),
            nullable=True,
            comment="URL to purchase from supplier (e.g., Amazon product link)",
        ),
    )

    # Add purchase_url to consumable_purchases table
    op.add_column(
        "consumable_purchases",
        sa.Column(
            "purchase_url",
            sa.String(500),
            nullable=True,
            comment="URL to purchase (e.g., Amazon product link)",
        ),
    )


def downgrade() -> None:
    """Remove URL fields from consumable tables."""
    op.drop_column("consumable_purchases", "purchase_url")
    op.drop_column("consumable_types", "supplier_url")
