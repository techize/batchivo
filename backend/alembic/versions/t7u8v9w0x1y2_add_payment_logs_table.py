"""Add payment_logs table for payment auditing.

Revision ID: t7u8v9w0x1y2
Revises: a1b2c3d4e5f6
Create Date: 2025-12-19 22:00:00.000000

This migration adds the payment_logs table to track all payment operations
including payments, refunds, webhooks, and status checks for auditing
and reconciliation purposes.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = "t7u8v9w0x1y2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create payment_logs table
    op.create_table(
        "payment_logs",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Timestamps
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
        # Order reference
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Associated order ID if available",
        ),
        sa.Column(
            "order_number",
            sa.String(50),
            nullable=True,
            comment="Order number used as idempotency key",
        ),
        # Payment provider
        sa.Column(
            "payment_provider",
            sa.String(50),
            nullable=False,
            server_default="square",
            comment="Payment provider (square, stripe, etc.)",
        ),
        # Square transaction IDs
        sa.Column(
            "payment_id",
            sa.String(255),
            nullable=True,
            comment="Square payment ID",
        ),
        sa.Column(
            "refund_id",
            sa.String(255),
            nullable=True,
            comment="Square refund ID (for refund operations)",
        ),
        # Operation type
        sa.Column(
            "operation",
            sa.String(50),
            nullable=False,
            server_default="payment",
            comment="Operation type: payment, refund, webhook, status_check",
        ),
        # Status
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="initiated",
            comment="Operation status: initiated, success, failed, retrying",
        ),
        # Amount
        sa.Column(
            "amount",
            sa.Integer(),
            nullable=True,
            comment="Amount in smallest currency unit (pence)",
        ),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=True,
            server_default="GBP",
            comment="Currency code",
        ),
        # Request/Response JSON
        sa.Column(
            "request_data",
            postgresql.JSONB(),
            nullable=True,
            comment="Request data sent to payment provider (sensitive data redacted)",
        ),
        sa.Column(
            "response_data",
            postgresql.JSONB(),
            nullable=True,
            comment="Response data from payment provider",
        ),
        # Error details
        sa.Column(
            "error_code",
            sa.String(100),
            nullable=True,
            comment="Error code from payment provider",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Human-readable error message",
        ),
        # Retry tracking
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Attempt number (1 for first try, 2+ for retries)",
        ),
        # Idempotency
        sa.Column(
            "idempotency_key",
            sa.String(255),
            nullable=True,
            comment="Idempotency key used for this operation",
        ),
        # Customer info
        sa.Column(
            "customer_email",
            sa.String(255),
            nullable=True,
            comment="Customer email for correlation",
        ),
        # Timing
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the operation started",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the operation completed (success or failure)",
        ),
        # Client info
        sa.Column(
            "client_ip",
            sa.String(45),
            nullable=True,
            comment="Client IP address",
        ),
        sa.Column(
            "user_agent",
            sa.String(500),
            nullable=True,
            comment="Client user agent string",
        ),
        # Primary key constraint
        sa.PrimaryKeyConstraint("id"),
        # Foreign key to orders
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes
    op.create_index("ix_payment_logs_order_id", "payment_logs", ["order_id"])
    op.create_index("ix_payment_logs_order_number", "payment_logs", ["order_number"])
    op.create_index("ix_payment_logs_payment_id", "payment_logs", ["payment_id"])
    op.create_index("ix_payment_logs_refund_id", "payment_logs", ["refund_id"])
    op.create_index("ix_payment_logs_operation", "payment_logs", ["operation"])
    op.create_index("ix_payment_logs_status", "payment_logs", ["status"])
    op.create_index("ix_payment_logs_idempotency_key", "payment_logs", ["idempotency_key"])
    op.create_index("ix_payment_logs_created_at", "payment_logs", ["created_at"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_payment_logs_created_at", table_name="payment_logs")
    op.drop_index("ix_payment_logs_idempotency_key", table_name="payment_logs")
    op.drop_index("ix_payment_logs_status", table_name="payment_logs")
    op.drop_index("ix_payment_logs_operation", table_name="payment_logs")
    op.drop_index("ix_payment_logs_refund_id", table_name="payment_logs")
    op.drop_index("ix_payment_logs_payment_id", table_name="payment_logs")
    op.drop_index("ix_payment_logs_order_number", table_name="payment_logs")
    op.drop_index("ix_payment_logs_order_id", table_name="payment_logs")
    # Drop table
    op.drop_table("payment_logs")
