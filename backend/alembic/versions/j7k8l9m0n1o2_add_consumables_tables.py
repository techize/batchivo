"""add_consumables_tables

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2025-12-05 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "j7k8l9m0n1o2"
down_revision: Union[str, Sequence[str], None] = "i6j7k8l9m0n1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create consumables tables for tracking magnets, inserts, hardware, etc."""

    # Create consumable_types table
    op.create_table(
        "consumable_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        # Identification
        sa.Column(
            "sku",
            sa.String(50),
            nullable=False,
            comment="Unique SKU within tenant (e.g., MAG-3X1, INS-M3)",
        ),
        sa.Column(
            "name",
            sa.String(200),
            nullable=False,
            comment="Human-readable name (e.g., Magnet 3mm x 1mm)",
        ),
        sa.Column("description", sa.Text(), nullable=True, comment="Detailed description"),
        sa.Column(
            "category",
            sa.String(100),
            nullable=True,
            comment="Category (magnets, inserts, hardware, finishing, packaging)",
        ),
        # Unit information
        sa.Column(
            "unit_of_measure",
            sa.String(20),
            nullable=False,
            server_default="each",
            comment="Unit of measure (each, ml, g, pack)",
        ),
        # Current pricing
        sa.Column(
            "current_cost_per_unit",
            sa.Numeric(10, 4),
            nullable=True,
            comment="Current cost per unit from latest purchase",
        ),
        # Stock management
        sa.Column(
            "quantity_on_hand",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Current stock quantity",
        ),
        sa.Column(
            "reorder_point",
            sa.Integer(),
            nullable=True,
            comment="Stock level that triggers reorder alert",
        ),
        sa.Column(
            "reorder_quantity",
            sa.Integer(),
            nullable=True,
            comment="Suggested quantity to order when reordering",
        ),
        # Supplier information
        sa.Column(
            "preferred_supplier",
            sa.String(200),
            nullable=True,
            comment="Preferred supplier/vendor name",
        ),
        sa.Column(
            "supplier_sku", sa.String(100), nullable=True, comment="Supplier SKU/product code"
        ),
        sa.Column(
            "typical_lead_days",
            sa.Integer(),
            nullable=True,
            comment="Typical delivery time in days",
        ),
        # Status
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether this consumable type is active",
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_consumable_types_tenant_id", "consumable_types", ["tenant_id"])
    op.create_index(
        "ix_consumable_types_sku", "consumable_types", ["tenant_id", "sku"], unique=True
    )
    op.create_index("ix_consumable_types_category", "consumable_types", ["category"])

    # Create consumable_purchases table
    op.create_table(
        "consumable_purchases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("consumable_type_id", sa.UUID(), nullable=False),
        # Purchase details
        sa.Column("quantity_purchased", sa.Integer(), nullable=False, comment="Quantity purchased"),
        sa.Column(
            "total_cost", sa.Numeric(10, 2), nullable=False, comment="Total cost of purchase"
        ),
        sa.Column(
            "cost_per_unit",
            sa.Numeric(10, 4),
            nullable=False,
            comment="Cost per unit (total_cost / quantity_purchased)",
        ),
        # Source
        sa.Column("supplier", sa.String(200), nullable=True, comment="Supplier/vendor name"),
        sa.Column(
            "order_reference", sa.String(100), nullable=True, comment="Order number or reference"
        ),
        sa.Column("purchase_date", sa.Date(), nullable=True, comment="Date of purchase"),
        # FIFO tracking
        sa.Column(
            "quantity_remaining",
            sa.Integer(),
            nullable=False,
            comment="Remaining quantity from this purchase (for FIFO costing)",
        ),
        sa.Column("notes", sa.Text(), nullable=True, comment="Additional notes"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["consumable_type_id"], ["consumable_types.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_consumable_purchases_tenant_id", "consumable_purchases", ["tenant_id"])
    op.create_index(
        "ix_consumable_purchases_consumable_type_id", "consumable_purchases", ["consumable_type_id"]
    )
    op.create_index(
        "ix_consumable_purchases_purchase_date", "consumable_purchases", ["purchase_date"]
    )

    # Create consumable_usage table
    op.create_table(
        "consumable_usage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("consumable_type_id", sa.UUID(), nullable=False),
        # Optional links to what caused the usage
        sa.Column(
            "production_run_id",
            sa.UUID(),
            nullable=True,
            comment="Production run that used this consumable",
        ),
        sa.Column(
            "product_id", sa.UUID(), nullable=True, comment="Product that used this consumable"
        ),
        # Usage details
        sa.Column(
            "quantity_used",
            sa.Integer(),
            nullable=False,
            comment="Quantity used (positive) or adjusted (negative for returns)",
        ),
        sa.Column(
            "cost_at_use",
            sa.Numeric(10, 4),
            nullable=True,
            comment="Cost per unit at time of use (snapshot for historical accuracy)",
        ),
        # Context
        sa.Column(
            "usage_type",
            sa.String(50),
            nullable=False,
            server_default="production",
            comment="Type of usage (production, adjustment, waste, return)",
        ),
        sa.Column(
            "notes", sa.Text(), nullable=True, comment="Usage notes or reason for adjustment"
        ),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # Keys
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["consumable_type_id"], ["consumable_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_consumable_usage_tenant_id", "consumable_usage", ["tenant_id"])
    op.create_index(
        "ix_consumable_usage_consumable_type_id", "consumable_usage", ["consumable_type_id"]
    )
    op.create_index(
        "ix_consumable_usage_production_run_id", "consumable_usage", ["production_run_id"]
    )
    op.create_index("ix_consumable_usage_product_id", "consumable_usage", ["product_id"])

    # Add consumable_type_id to product_components table
    op.add_column(
        "product_components",
        sa.Column(
            "consumable_type_id",
            sa.UUID(),
            nullable=True,
            comment="Link to consumable type for automatic cost/inventory tracking",
        ),
    )
    op.create_foreign_key(
        "fk_product_components_consumable_type_id",
        "product_components",
        "consumable_types",
        ["consumable_type_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_product_components_consumable_type_id", "product_components", ["consumable_type_id"]
    )


def downgrade() -> None:
    """Drop consumables tables and related columns."""
    # Remove column from product_components
    op.drop_index("ix_product_components_consumable_type_id", "product_components")
    op.drop_constraint(
        "fk_product_components_consumable_type_id", "product_components", type_="foreignkey"
    )
    op.drop_column("product_components", "consumable_type_id")

    # Drop tables in reverse order
    op.drop_table("consumable_usage")
    op.drop_table("consumable_purchases")
    op.drop_table("consumable_types")
