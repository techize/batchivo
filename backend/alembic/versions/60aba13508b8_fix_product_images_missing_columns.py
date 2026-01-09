"""fix_product_images_missing_columns

Revision ID: 60aba13508b8
Revises: b624b63926e9
Create Date: 2025-12-16 16:19:44.504061

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "60aba13508b8"
down_revision: Union[str, Sequence[str], None] = "b624b63926e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :table AND column_name = :column
            )
        """),
        {"table": table_name, "column": column_name},
    )
    return result.scalar()


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = :name
            )
        """),
        {"name": index_name},
    )
    return result.scalar()


def constraint_exists(constraint_name: str) -> bool:
    """Check if a constraint exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = :name
            )
        """),
        {"name": constraint_name},
    )
    return result.scalar()


def upgrade() -> None:
    """Upgrade schema."""
    # Fix product_images table missing columns from modified migration
    # The original migration 377444db97ce was modified after being applied,
    # so these columns were never added to production.
    #
    # This migration is idempotent - it checks if columns exist before adding.
    # This handles both fresh databases (where 377444db97ce created everything)
    # and production (where the original 377444db97ce didn't have these columns).

    # Add tenant_id column (required for multi-tenant isolation)
    if not column_exists("product_images", "tenant_id"):
        op.add_column(
            "product_images",
            sa.Column(
                "tenant_id",
                sa.Uuid(),
                nullable=True,  # Start nullable to allow backfill
                comment="Tenant ID for multi-tenant isolation",
            ),
        )

        # Backfill tenant_id from the related product
        op.execute("""
            UPDATE product_images
            SET tenant_id = products.tenant_id
            FROM products
            WHERE product_images.product_id = products.id
        """)

        # Now make tenant_id NOT NULL
        op.alter_column("product_images", "tenant_id", nullable=False)

    # Add index on tenant_id
    if not index_exists("ix_product_images_tenant_id"):
        op.create_index(
            op.f("ix_product_images_tenant_id"), "product_images", ["tenant_id"], unique=False
        )

    # Add foreign key constraint
    if not constraint_exists("fk_product_images_tenant_id"):
        op.create_foreign_key(
            "fk_product_images_tenant_id",
            "product_images",
            "tenants",
            ["tenant_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Add other missing columns
    if not column_exists("product_images", "original_filename"):
        op.add_column(
            "product_images",
            sa.Column(
                "original_filename",
                sa.String(length=255),
                nullable=True,
                comment="Original uploaded filename",
            ),
        )

    if not column_exists("product_images", "file_size"):
        op.add_column(
            "product_images",
            sa.Column("file_size", sa.Integer(), nullable=True, comment="File size in bytes"),
        )

    if not column_exists("product_images", "content_type"):
        op.add_column(
            "product_images",
            sa.Column(
                "content_type",
                sa.String(length=100),
                nullable=True,
                comment="MIME type of the image",
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove added columns in reverse order
    op.drop_column("product_images", "content_type")
    op.drop_column("product_images", "file_size")
    op.drop_column("product_images", "original_filename")
    op.drop_constraint("fk_product_images_tenant_id", "product_images", type_="foreignkey")
    op.drop_index(op.f("ix_product_images_tenant_id"), table_name="product_images")
    op.drop_column("product_images", "tenant_id")
