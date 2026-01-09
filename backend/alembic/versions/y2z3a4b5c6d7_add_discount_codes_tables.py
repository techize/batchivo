"""Add discount_codes and discount_usages tables.

Revision ID: y2z3a4b5c6d7
Revises: x1y2z3a4b5c6
Create Date: 2025-12-29 18:00:00.000000

This migration adds:
- discount_codes table for promotional pricing configuration
- discount_usages table for tracking individual discount usage
- Unique constraint on discount code per tenant
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "y2z3a4b5c6d7"
down_revision = "x1y2z3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create discount_codes table
    op.create_table(
        "discount_codes",
        # Primary key (UUIDMixin)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Tenant isolation
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant ID for multi-tenant isolation",
        ),
        # Code identification
        sa.Column(
            "code",
            sa.String(50),
            nullable=False,
            comment="Discount code (uppercase, unique per tenant)",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Display name for the discount",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Internal description of the discount",
        ),
        # Discount configuration
        sa.Column(
            "discount_type",
            sa.String(20),
            nullable=False,
            comment="Type of discount: percentage or fixed_amount",
        ),
        sa.Column(
            "amount",
            sa.Numeric(10, 2),
            nullable=False,
            comment="Discount amount (percentage 0-100 or fixed amount in GBP)",
        ),
        # Constraints
        sa.Column(
            "min_order_amount",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Minimum order subtotal required to use this discount",
        ),
        sa.Column(
            "max_discount_amount",
            sa.Numeric(10, 2),
            nullable=True,
            comment="Maximum discount amount (caps percentage discounts)",
        ),
        # Usage limits
        sa.Column(
            "max_uses",
            sa.Integer(),
            nullable=True,
            comment="Maximum total uses (null = unlimited)",
        ),
        sa.Column(
            "max_uses_per_customer",
            sa.Integer(),
            nullable=True,
            comment="Maximum uses per customer email (null = unlimited)",
        ),
        sa.Column(
            "current_uses",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Current number of times this code has been used",
        ),
        # Validity period
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Start of validity period",
        ),
        sa.Column(
            "valid_to",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="End of validity period (null = no expiry)",
        ),
        # Status
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether the discount is currently active",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        # Unique constraint: code must be unique per tenant
        sa.UniqueConstraint("tenant_id", "code", name="uq_discount_codes_tenant_code"),
        comment="Discount codes for promotional pricing",
    )

    # Create indexes for discount_codes
    op.create_index("ix_discount_codes_tenant_id", "discount_codes", ["tenant_id"])
    op.create_index("ix_discount_codes_code", "discount_codes", ["code"])
    op.create_index("ix_discount_codes_is_active", "discount_codes", ["is_active"])

    # Create discount_usages table
    op.create_table(
        "discount_usages",
        # Primary key (UUIDMixin)
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Tenant isolation
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Tenant ID for multi-tenant isolation",
        ),
        # References
        sa.Column(
            "discount_code_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="The discount code that was used",
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="The order this discount was applied to",
        ),
        # Customer identification
        sa.Column(
            "customer_email",
            sa.String(255),
            nullable=False,
            comment="Customer email for per-customer limit tracking",
        ),
        # Applied discount
        sa.Column(
            "discount_amount",
            sa.Numeric(10, 2),
            nullable=False,
            comment="Actual discount amount applied to this order",
        ),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["discount_code_id"],
            ["discount_codes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
    )

    # Create indexes for discount_usages
    op.create_index("ix_discount_usages_tenant_id", "discount_usages", ["tenant_id"])
    op.create_index("ix_discount_usages_discount_code_id", "discount_usages", ["discount_code_id"])
    op.create_index("ix_discount_usages_order_id", "discount_usages", ["order_id"])
    op.create_index("ix_discount_usages_customer_email", "discount_usages", ["customer_email"])


def downgrade() -> None:
    # Drop discount_usages indexes
    op.drop_index("ix_discount_usages_customer_email", table_name="discount_usages")
    op.drop_index("ix_discount_usages_order_id", table_name="discount_usages")
    op.drop_index("ix_discount_usages_discount_code_id", table_name="discount_usages")
    op.drop_index("ix_discount_usages_tenant_id", table_name="discount_usages")
    # Drop discount_usages table
    op.drop_table("discount_usages")

    # Drop discount_codes indexes
    op.drop_index("ix_discount_codes_is_active", table_name="discount_codes")
    op.drop_index("ix_discount_codes_code", table_name="discount_codes")
    op.drop_index("ix_discount_codes_tenant_id", table_name="discount_codes")
    # Drop discount_codes table
    op.drop_table("discount_codes")
