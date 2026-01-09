"""Add tenant_id to product_variants

Revision ID: f0g1h2i3j4k5
Revises: e9f0g1h2i3j4
Create Date: 2026-01-01 19:45:00.000000

This migration adds tenant_id to product_variants for multi-tenant consistency
and RLS (Row Level Security) enforcement.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "f0g1h2i3j4k5"
down_revision = "e9f0g1h2i3j4"
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


def upgrade() -> None:
    """Add tenant_id column and populate from parent product."""
    # Skip if table doesn't exist (not deployed in this environment)
    if not table_exists("product_variants"):
        return

    # 1. Add the column as nullable first
    op.add_column(
        "product_variants",
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=True,
            comment="Tenant ID for multi-tenant isolation",
        ),
    )

    # 2. Populate tenant_id from the parent product's tenant_id
    op.execute("""
        UPDATE product_variants pv
        SET tenant_id = p.tenant_id
        FROM products p
        WHERE pv.product_id = p.id
    """)

    # 3. Make the column NOT NULL
    op.alter_column(
        "product_variants",
        "tenant_id",
        nullable=False,
    )

    # 4. Add foreign key constraint
    op.create_foreign_key(
        "fk_product_variants_tenant_id",
        "product_variants",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 5. Add index for performance
    op.create_index(
        "ix_product_variants_tenant_id",
        "product_variants",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Remove tenant_id column."""
    if not table_exists("product_variants"):
        return
    op.drop_index("ix_product_variants_tenant_id", table_name="product_variants")
    op.drop_constraint("fk_product_variants_tenant_id", "product_variants", type_="foreignkey")
    op.drop_column("product_variants", "tenant_id")
