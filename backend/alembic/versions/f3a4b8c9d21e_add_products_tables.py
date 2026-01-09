"""add_products_tables

Revision ID: f3a4b8c9d21e
Revises: 8cee3531b555
Create Date: 2025-11-06 20:48:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f3a4b8c9d21e"
down_revision: Union[str, Sequence[str], None] = "8cee3531b555"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create products table
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column(
            "labor_hours", sa.Numeric(precision=10, scale=2), server_default="0", nullable=False
        ),
        sa.Column("labor_rate_override", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "overhead_percentage",
            sa.Numeric(precision=5, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),
        comment="Product catalog with Bill of Materials and cost tracking",
    )

    # Create indices for products
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_sku", "products", ["sku"])
    op.create_index("ix_products_category", "products", ["category"])

    # Create product_materials table (Bill of Materials)
    op.create_table(
        "product_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("spool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("weight_grams", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("cost_per_gram", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spool_id"], ["spools.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices for product_materials
    op.create_index("ix_product_materials_product_id", "product_materials", ["product_id"])
    op.create_index("ix_product_materials_spool_id", "product_materials", ["spool_id"])

    # Create product_components table
    op.create_table(
        "product_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("supplier", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index for product_components
    op.create_index("ix_product_components_product_id", "product_components", ["product_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order (handle foreign keys)
    op.drop_index("ix_product_components_product_id", table_name="product_components")
    op.drop_table("product_components")

    op.drop_index("ix_product_materials_spool_id", table_name="product_materials")
    op.drop_index("ix_product_materials_product_id", table_name="product_materials")
    op.drop_table("product_materials")

    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_tenant_id", table_name="products")
    op.drop_table("products")
