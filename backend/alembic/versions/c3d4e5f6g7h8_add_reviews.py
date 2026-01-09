"""Add reviews table and product review stats

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-12-29 19:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create reviews table
    op.create_table(
        "reviews",
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
            "product_id",
            sa.UUID(),
            nullable=False,
            comment="Product being reviewed",
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            nullable=True,
            comment="Customer account if logged in when submitting",
        ),
        sa.Column(
            "customer_email",
            sa.String(length=255),
            nullable=False,
            comment="Reviewer email address",
        ),
        sa.Column(
            "customer_name",
            sa.String(length=255),
            nullable=False,
            comment="Reviewer display name",
        ),
        sa.Column(
            "rating",
            sa.Integer(),
            nullable=False,
            comment="Star rating (1-5)",
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=True,
            comment="Review title/headline",
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=False,
            comment="Review body text",
        ),
        sa.Column(
            "is_verified_purchase",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Whether reviewer has purchased this product",
        ),
        sa.Column(
            "order_id",
            sa.UUID(),
            nullable=True,
            comment="Order that verified this purchase",
        ),
        sa.Column(
            "is_approved",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Whether review is approved for display",
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When review was approved",
        ),
        sa.Column(
            "approved_by",
            sa.UUID(),
            nullable=True,
            comment="Admin user who approved the review",
        ),
        sa.Column(
            "rejection_reason",
            sa.String(length=500),
            nullable=True,
            comment="Reason for rejection if not approved",
        ),
        sa.Column(
            "helpful_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of 'helpful' votes",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
        comment="Customer product reviews with moderation",
    )
    op.create_index(op.f("ix_reviews_tenant_id"), "reviews", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_reviews_product_id"), "reviews", ["product_id"], unique=False)
    op.create_index(op.f("ix_reviews_customer_id"), "reviews", ["customer_id"], unique=False)
    op.create_index(op.f("ix_reviews_customer_email"), "reviews", ["customer_email"], unique=False)
    op.create_index(op.f("ix_reviews_is_approved"), "reviews", ["is_approved"], unique=False)
    op.create_index(op.f("ix_reviews_order_id"), "reviews", ["order_id"], unique=False)

    # Add review statistics columns to products table
    op.add_column(
        "products",
        sa.Column(
            "average_rating",
            sa.Numeric(precision=3, scale=2),
            nullable=True,
            comment="Average review rating (1.00-5.00), null if no reviews",
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "review_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of approved reviews",
        ),
    )


def downgrade() -> None:
    # Remove review stats from products
    op.drop_column("products", "review_count")
    op.drop_column("products", "average_rating")

    # Drop reviews table
    op.drop_index(op.f("ix_reviews_order_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_is_approved"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_customer_email"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_customer_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_product_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_tenant_id"), table_name="reviews")
    op.drop_table("reviews")
