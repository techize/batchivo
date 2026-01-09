"""Add product_components table for composite products

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2025-12-09 09:30:00.000000

This migration adds support for composite products (bundles/sets).
A Product can now contain other Products as components, enabling:
- "Finger Dino Set" = Finger Dino Egg + Steggy Model
- "Mega Bundle" = Product A + Product B + Product C

The product_components table links parent products to child products with quantity.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "o2p3q4r5s6t7"
down_revision = "n1o2p3q4r5s6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_components table (Product -> Product relationship)
    op.create_table(
        "product_components",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "parent_product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "child_product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Constraints
        sa.CheckConstraint("quantity > 0", name="check_product_component_quantity_positive"),
        sa.CheckConstraint("parent_product_id != child_product_id", name="check_no_self_reference"),
        sa.UniqueConstraint(
            "parent_product_id", "child_product_id", name="uq_product_component_parent_child"
        ),
    )

    # Create indexes for efficient querying
    op.create_index("idx_product_components_parent", "product_components", ["parent_product_id"])
    op.create_index("idx_product_components_child", "product_components", ["child_product_id"])


def downgrade() -> None:
    op.drop_index("idx_product_components_child", table_name="product_components")
    op.drop_index("idx_product_components_parent", table_name="product_components")
    op.drop_table("product_components")
