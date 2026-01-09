"""Add customers and customer_addresses tables

Revision ID: b2c3d4e5f6g7
Revises: z3a4b5c6d7e8
Create Date: 2025-12-29 18:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "z3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
            comment="Tenant ID for multi-tenant isolation",
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
            comment="Customer email address (unique per tenant)",
        ),
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=False,
            comment="Bcrypt hashed password",
        ),
        sa.Column(
            "full_name",
            sa.String(length=255),
            nullable=False,
            comment="Customer full name",
        ),
        sa.Column(
            "phone",
            sa.String(length=50),
            nullable=True,
            comment="Customer phone number",
        ),
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Whether email address is verified",
        ),
        sa.Column(
            "email_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When email was verified",
        ),
        sa.Column(
            "email_verification_token",
            sa.String(length=255),
            nullable=True,
            comment="Email verification token",
        ),
        sa.Column(
            "email_verification_expires",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When verification token expires",
        ),
        sa.Column(
            "reset_token",
            sa.String(length=255),
            nullable=True,
            comment="Password reset token",
        ),
        sa.Column(
            "reset_token_expires",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When reset token expires",
        ),
        sa.Column(
            "marketing_consent",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Whether customer consented to marketing emails",
        ),
        sa.Column(
            "marketing_consent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When marketing consent was given",
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last login timestamp",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            default=True,
            comment="Whether customer account is active",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_customer_tenant_email"),
        comment="Customer accounts for shop storefronts",
    )
    op.create_index(op.f("ix_customers_tenant_id"), "customers", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_customers_email"), "customers", ["email"], unique=False)

    # Create customer_addresses table
    op.create_table(
        "customer_addresses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "customer_id",
            sa.UUID(),
            nullable=False,
            comment="Customer ID",
        ),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            nullable=False,
            comment="Tenant ID for multi-tenant isolation",
        ),
        sa.Column(
            "label",
            sa.String(length=50),
            nullable=False,
            default="Home",
            comment="Address label (Home, Work, etc.)",
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Whether this is the default address",
        ),
        sa.Column(
            "recipient_name",
            sa.String(length=255),
            nullable=False,
            comment="Recipient name for this address",
        ),
        sa.Column(
            "phone",
            sa.String(length=50),
            nullable=True,
            comment="Contact phone for this address",
        ),
        sa.Column(
            "line1",
            sa.String(length=255),
            nullable=False,
            comment="Address line 1",
        ),
        sa.Column(
            "line2",
            sa.String(length=255),
            nullable=True,
            comment="Address line 2",
        ),
        sa.Column(
            "city",
            sa.String(length=100),
            nullable=False,
            comment="City",
        ),
        sa.Column(
            "county",
            sa.String(length=100),
            nullable=True,
            comment="County/State",
        ),
        sa.Column(
            "postcode",
            sa.String(length=20),
            nullable=False,
            comment="Postcode/ZIP",
        ),
        sa.Column(
            "country",
            sa.String(length=100),
            nullable=False,
            default="United Kingdom",
            comment="Country",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_customer_addresses_customer_id"),
        "customer_addresses",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_customer_addresses_tenant_id"),
        "customer_addresses",
        ["tenant_id"],
        unique=False,
    )

    # Add customer_id to orders table
    op.add_column(
        "orders",
        sa.Column(
            "customer_id",
            sa.UUID(),
            nullable=True,
            comment="Customer account if logged in during purchase",
        ),
    )
    op.create_foreign_key(
        "fk_orders_customer_id",
        "orders",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_orders_customer_id"), "orders", ["customer_id"], unique=False)


def downgrade() -> None:
    # Remove customer_id from orders
    op.drop_index(op.f("ix_orders_customer_id"), table_name="orders")
    op.drop_constraint("fk_orders_customer_id", "orders", type_="foreignkey")
    op.drop_column("orders", "customer_id")

    # Drop customer_addresses table
    op.drop_index(op.f("ix_customer_addresses_tenant_id"), table_name="customer_addresses")
    op.drop_index(op.f("ix_customer_addresses_customer_id"), table_name="customer_addresses")
    op.drop_table("customer_addresses")

    # Drop customers table
    op.drop_index(op.f("ix_customers_email"), table_name="customers")
    op.drop_index(op.f("ix_customers_tenant_id"), table_name="customers")
    op.drop_table("customers")
