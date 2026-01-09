"""Add return_requests and return_items tables for RMA system

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-12-29 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create return_requests table
    op.create_table(
        "return_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "rma_number",
            sa.String(50),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "order_id",
            sa.UUID(),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("customer_email", sa.String(255), nullable=False, index=True),
        sa.Column("customer_name", sa.String(255), nullable=False),
        # Return details
        sa.Column(
            "status",
            sa.Enum(
                "requested",
                "approved",
                "received",
                "completed",
                "rejected",
                "cancelled",
                name="returnstatus",
            ),
            nullable=False,
            default="requested",
            index=True,
        ),
        sa.Column(
            "reason",
            sa.Enum(
                "defective",
                "wrong_item",
                "not_as_described",
                "changed_mind",
                "damaged_shipping",
                "missing_parts",
                "other",
                name="returnreason",
            ),
            nullable=False,
        ),
        sa.Column("reason_details", sa.Text(), nullable=True),
        sa.Column(
            "requested_action",
            sa.Enum(
                "refund",
                "replacement",
                "repair",
                "store_credit",
                name="returnaction",
            ),
            nullable=False,
            default="refund",
        ),
        # Admin notes
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        # Workflow timestamps
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "received_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "completed_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Resolution
        sa.Column("refund_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("refund_reference", sa.String(255), nullable=True),
        sa.Column(
            "replacement_order_id",
            sa.UUID(),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Return shipping
        sa.Column("return_tracking_number", sa.String(100), nullable=True),
        sa.Column("return_label_url", sa.String(500), nullable=True),
        # Primary key
        sa.PrimaryKeyConstraint("id"),
    )

    # Create return_items table
    op.create_table(
        "return_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "return_request_id",
            sa.UUID(),
            sa.ForeignKey("return_requests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "order_item_id",
            sa.UUID(),
            sa.ForeignKey("order_items.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False, default=1),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("condition_notes", sa.String(500), nullable=True),
        sa.Column("is_restockable", sa.Boolean(), nullable=False, default=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("return_items")
    op.drop_table("return_requests")
    # Drop enums
    op.execute("DROP TYPE IF EXISTS returnstatus")
    op.execute("DROP TYPE IF EXISTS returnreason")
    op.execute("DROP TYPE IF EXISTS returnaction")
