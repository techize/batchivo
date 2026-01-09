"""Add PostgreSQL full-text search to products

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2025-12-30 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f6g7h8i9j0k1"
down_revision: Union[str, None] = "e5f6g7h8i9j0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if we're on PostgreSQL (SQLite doesn't support tsvector)
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # Skip FTS setup for SQLite - search service falls back to LIKE
        return

    # Add tsvector column for full-text search
    op.add_column(
        "products",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR,
            nullable=True,
        ),
    )

    # Create GIN index for fast full-text search
    op.create_index(
        "ix_products_search_vector",
        "products",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Create trigger function to auto-update search_vector
    op.execute("""
        CREATE OR REPLACE FUNCTION products_search_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.sku, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(NEW.shop_description, '')), 'C');
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to run function on INSERT or UPDATE
    op.execute("""
        CREATE TRIGGER products_search_update
            BEFORE INSERT OR UPDATE ON products
            FOR EACH ROW
            EXECUTE FUNCTION products_search_trigger();
    """)

    # Populate search_vector for existing products
    op.execute("""
        UPDATE products
        SET search_vector = (
            setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(sku, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(description, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(shop_description, '')), 'C')
        );
    """)


def downgrade() -> None:
    # Check if we're on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS products_search_update ON products")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS products_search_trigger()")

    # Drop index
    op.drop_index("ix_products_search_vector", table_name="products")

    # Drop column
    op.drop_column("products", "search_vector")
