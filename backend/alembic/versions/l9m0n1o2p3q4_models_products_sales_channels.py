"""Rename products to models, add new products and sales channels

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2024-12-05 20:15:00.000000

This migration:
1. Renames 'products' table to 'models' (printed items)
2. Renames 'product_materials' to 'model_materials'
3. Renames 'product_components' to 'model_components'
4. Creates new 'products' table (sellable items composed of models)
5. Creates 'product_models' join table
6. Creates 'sales_channels' table
7. Creates 'product_pricing' table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = "l9m0n1o2p3q4"
down_revision = "k8l9m0n1o2p3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================
    # Step 1: Rename products -> models
    # ========================================

    # Drop the foreign key constraint from production_run_items first
    op.drop_constraint(
        "production_run_items_product_id_fkey", "production_run_items", type_="foreignkey"
    )

    # Drop the unique constraint before renaming
    op.drop_constraint("uq_product_tenant_sku", "products", type_="unique")

    # Rename the table
    op.rename_table("products", "models")

    # Recreate unique constraint with new name
    op.create_unique_constraint("uq_model_tenant_sku", "models", ["tenant_id", "sku"])

    # Rename the column in production_run_items
    op.alter_column("production_run_items", "product_id", new_column_name="model_id")

    # Recreate the foreign key with new reference
    op.create_foreign_key(
        "production_run_items_model_id_fkey",
        "production_run_items",
        "models",
        ["model_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Update index name
    op.drop_index("idx_production_run_items_product", table_name="production_run_items")
    op.create_index("idx_production_run_items_model", "production_run_items", ["model_id"])

    # ========================================
    # Step 1b: Update consumable_usage product_id -> model_id
    # ========================================

    # Drop foreign key constraint if it exists
    try:
        op.drop_constraint(
            "consumable_usage_product_id_fkey", "consumable_usage", type_="foreignkey"
        )
    except Exception:
        pass  # Constraint might not exist

    # Rename column
    op.alter_column("consumable_usage", "product_id", new_column_name="model_id")

    # Recreate foreign key pointing to models
    op.create_foreign_key(
        "consumable_usage_model_id_fkey",
        "consumable_usage",
        "models",
        ["model_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ========================================
    # Step 2: Rename product_materials -> model_materials
    # ========================================

    # Drop foreign key to products (now models)
    op.drop_constraint("product_materials_product_id_fkey", "product_materials", type_="foreignkey")

    # Rename table
    op.rename_table("product_materials", "model_materials")

    # Rename column
    op.alter_column("model_materials", "product_id", new_column_name="model_id")

    # Recreate foreign key
    op.create_foreign_key(
        "model_materials_model_id_fkey",
        "model_materials",
        "models",
        ["model_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ========================================
    # Step 3: Rename product_components -> model_components
    # ========================================

    # Drop foreign key to products (now models)
    op.drop_constraint(
        "product_components_product_id_fkey", "product_components", type_="foreignkey"
    )

    # Rename table
    op.rename_table("product_components", "model_components")

    # Rename column
    op.alter_column("model_components", "product_id", new_column_name="model_id")

    # Recreate foreign key
    op.create_foreign_key(
        "model_components_model_id_fkey",
        "model_components",
        "models",
        ["model_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ========================================
    # Step 4: Create sales_channels table
    # ========================================
    op.create_table(
        "sales_channels",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "platform_type", sa.String(50), nullable=False
        ),  # fair, online_shop, shopify, ebay, etsy, other
        sa.Column("fee_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("fee_fixed", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("monthly_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("tenant_id", "name", name="uq_sales_channel_tenant_name"),
        sa.CheckConstraint(
            "platform_type IN ('fair', 'online_shop', 'shopify', 'ebay', 'etsy', 'amazon', 'other')",
            name="check_platform_type",
        ),
    )
    op.create_index("idx_sales_channels_tenant", "sales_channels", ["tenant_id"])

    # ========================================
    # Step 5: Create new products table (sellable items)
    # ========================================
    op.create_table(
        "products",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("units_in_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("packaging_cost", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("assembly_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),
    )
    op.create_index("idx_products_tenant", "products", ["tenant_id"])
    op.create_index("idx_products_sku", "products", ["sku"])

    # ========================================
    # Step 6: Create product_models join table
    # ========================================
    op.create_table(
        "product_models",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_id",
            UUID(as_uuid=True),
            sa.ForeignKey("models.id", ondelete="RESTRICT"),
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
        sa.CheckConstraint("quantity > 0", name="check_quantity_positive"),
    )
    op.create_index("idx_product_models_product", "product_models", ["product_id"])
    op.create_index("idx_product_models_model", "product_models", ["model_id"])

    # ========================================
    # Step 7: Create product_pricing table
    # ========================================
    op.create_table(
        "product_pricing",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sales_channel_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sales_channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("list_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("product_id", "sales_channel_id", name="uq_product_channel_pricing"),
    )
    op.create_index("idx_product_pricing_product", "product_pricing", ["product_id"])
    op.create_index("idx_product_pricing_channel", "product_pricing", ["sales_channel_id"])


def downgrade() -> None:
    # Drop new tables
    op.drop_table("product_pricing")
    op.drop_table("product_models")
    op.drop_table("products")
    op.drop_table("sales_channels")

    # Restore consumable_usage model_id -> product_id
    try:
        op.drop_constraint("consumable_usage_model_id_fkey", "consumable_usage", type_="foreignkey")
    except Exception:
        pass
    op.alter_column("consumable_usage", "model_id", new_column_name="product_id")

    # Rename model_components back to product_components
    op.drop_constraint("model_components_model_id_fkey", "model_components", type_="foreignkey")
    op.alter_column("model_components", "model_id", new_column_name="product_id")
    op.rename_table("model_components", "product_components")

    # Rename model_materials back to product_materials
    op.drop_constraint("model_materials_model_id_fkey", "model_materials", type_="foreignkey")
    op.alter_column("model_materials", "model_id", new_column_name="product_id")
    op.rename_table("model_materials", "product_materials")

    # Rename models back to products
    op.drop_constraint("uq_model_tenant_sku", "models", type_="unique")
    op.drop_constraint(
        "production_run_items_model_id_fkey", "production_run_items", type_="foreignkey"
    )
    op.drop_index("idx_production_run_items_model", table_name="production_run_items")
    op.alter_column("production_run_items", "model_id", new_column_name="product_id")
    op.rename_table("models", "products")
    op.create_unique_constraint("uq_product_tenant_sku", "products", ["tenant_id", "sku"])

    # Recreate foreign keys pointing to products
    op.create_foreign_key(
        "production_run_items_product_id_fkey",
        "production_run_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("idx_production_run_items_product", "production_run_items", ["product_id"])

    op.create_foreign_key(
        "product_materials_product_id_fkey",
        "product_materials",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "product_components_product_id_fkey",
        "product_components",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )
