"""Add pages table for content management

Revision ID: w0x1y2z3a4b5
Revises: v9w0x1y2z3a4
Create Date: 2025-12-29 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "w0x1y2z3a4b5"
down_revision: Union[str, Sequence[str], None] = "v9w0x1y2z3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pages",
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            nullable=False,
            comment="Tenant ID for multi-tenant isolation",
        ),
        sa.Column(
            "slug",
            sa.String(length=100),
            nullable=False,
            comment="URL-friendly identifier (e.g., 'privacy-policy')",
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
            comment="Page title displayed to users",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            server_default="",
            comment="Page content in Markdown format",
        ),
        sa.Column(
            "page_type",
            sa.String(length=20),
            nullable=False,
            server_default="policy",
            comment="Page type: policy, info, legal",
        ),
        sa.Column(
            "meta_description",
            sa.String(length=300),
            nullable=True,
            comment="SEO meta description",
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether page is publicly visible",
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Sort order for page listings",
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_page_tenant_slug"),
        comment="Content pages for policies and information",
    )
    op.create_index(op.f("ix_pages_slug"), "pages", ["slug"], unique=False)
    op.create_index(op.f("ix_pages_tenant_id"), "pages", ["tenant_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_pages_tenant_id"), table_name="pages")
    op.drop_index(op.f("ix_pages_slug"), table_name="pages")
    op.drop_table("pages")
