"""Add webhook events and dead letter tables.

Revision ID: 8e9eb6466afa
Revises: z3a4b5c6d7e8
Create Date: 2026-01-19 16:00:00.000000

This migration adds tables for:
- webhook_events: Tracks inbound webhook events for idempotency and retry logic
- webhook_dead_letters: Dead letter queue for permanently failed webhook events
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "8e9eb6466afa"
down_revision = "z3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhook_events table
    op.create_table(
        "webhook_events",
        # UUID primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Event identification
        sa.Column(
            "event_id",
            sa.String(255),
            nullable=False,
            comment="Unique event ID from the webhook provider",
        ),
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            server_default="square",
            comment="Webhook source (square, stripe, etc.)",
        ),
        sa.Column(
            "event_type",
            sa.String(100),
            nullable=False,
            comment="Type of webhook event",
        ),
        # Processing status
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="received",
            comment="Processing status (received, processing, completed, failed, dead_letter)",
        ),
        # Full webhook payload
        sa.Column(
            "payload",
            JSONB,
            nullable=False,
            comment="Full webhook payload as received",
        ),
        # Extracted data for quick access
        sa.Column(
            "payment_id",
            sa.String(255),
            nullable=True,
            comment="Square payment ID if applicable",
        ),
        sa.Column(
            "refund_id",
            sa.String(255),
            nullable=True,
            comment="Square refund ID if applicable",
        ),
        sa.Column(
            "order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="SET NULL"),
            nullable=True,
            comment="Associated order ID if found",
        ),
        # Retry tracking
        sa.Column(
            "attempt_count",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Number of processing attempts",
        ),
        sa.Column(
            "max_attempts",
            sa.Integer,
            nullable=False,
            server_default="5",
            comment="Maximum number of retry attempts",
        ),
        sa.Column(
            "next_retry_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Scheduled time for next retry",
        ),
        # Processing timestamps
        sa.Column(
            "first_received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the event was first received",
        ),
        sa.Column(
            "last_processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the event was last processed",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When processing completed successfully",
        ),
        # Error tracking
        sa.Column(
            "error_message",
            sa.Text,
            nullable=True,
            comment="Error message from last failed attempt",
        ),
        sa.Column(
            "error_details",
            JSONB,
            nullable=True,
            comment="Detailed error information (stack trace, context)",
        ),
        # Processing result
        sa.Column(
            "processing_result",
            JSONB,
            nullable=True,
            comment="Result of successful processing",
        ),
        # Signature validation
        sa.Column(
            "signature_valid",
            sa.Boolean,
            nullable=True,
            comment="Whether webhook signature was valid",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="Inbound webhook events for idempotency and retry handling",
    )

    # Create indexes for webhook_events
    op.create_index("ix_webhook_events_event_id", "webhook_events", ["event_id"])
    op.create_index("ix_webhook_events_source", "webhook_events", ["source"])
    op.create_index("ix_webhook_events_event_type", "webhook_events", ["event_type"])
    op.create_index("ix_webhook_events_status", "webhook_events", ["status"])
    op.create_index("ix_webhook_events_payment_id", "webhook_events", ["payment_id"])
    op.create_index("ix_webhook_events_refund_id", "webhook_events", ["refund_id"])
    op.create_index("ix_webhook_events_order_id", "webhook_events", ["order_id"])
    op.create_index("ix_webhook_events_next_retry_at", "webhook_events", ["next_retry_at"])

    # Unique constraint for idempotency
    op.create_index(
        "ix_webhook_events_idempotency",
        "webhook_events",
        ["event_id", "source"],
        unique=True,
    )

    # Index for finding events to retry
    op.create_index(
        "ix_webhook_events_retry",
        "webhook_events",
        ["status", "next_retry_at"],
    )

    # Index for monitoring/debugging
    op.create_index(
        "ix_webhook_events_status_type",
        "webhook_events",
        ["status", "event_type"],
    )

    # Create webhook_dead_letters table
    op.create_table(
        "webhook_dead_letters",
        # UUID primary key
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Reference to original event
        sa.Column(
            "webhook_event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("webhook_events.id", ondelete="CASCADE"),
            nullable=False,
            comment="Original webhook event that failed",
        ),
        # Copy of key fields for easy querying
        sa.Column(
            "source",
            sa.String(50),
            nullable=False,
            comment="Webhook source",
        ),
        sa.Column(
            "event_id",
            sa.String(255),
            nullable=False,
            comment="Original event ID",
        ),
        sa.Column(
            "event_type",
            sa.String(100),
            nullable=False,
            comment="Event type",
        ),
        # Failure details
        sa.Column(
            "failure_reason",
            sa.Text,
            nullable=False,
            comment="Summary of why processing failed",
        ),
        sa.Column(
            "total_attempts",
            sa.Integer,
            nullable=False,
            comment="Total number of attempts made",
        ),
        sa.Column(
            "first_failure_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the first failure occurred",
        ),
        sa.Column(
            "last_failure_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the last failure occurred",
        ),
        # Error history
        sa.Column(
            "error_history",
            JSONB,
            nullable=True,
            comment="List of all errors encountered",
        ),
        # Resolution tracking
        sa.Column(
            "resolved",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="Whether this has been manually resolved",
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When it was resolved",
        ),
        sa.Column(
            "resolved_by",
            sa.String(255),
            nullable=True,
            comment="Who resolved it (user email or system)",
        ),
        sa.Column(
            "resolution_notes",
            sa.Text,
            nullable=True,
            comment="Notes about how it was resolved",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        comment="Dead letter queue for permanently failed webhook events",
    )

    # Create indexes for webhook_dead_letters
    op.create_index(
        "ix_webhook_dead_letters_webhook_event_id",
        "webhook_dead_letters",
        ["webhook_event_id"],
    )
    op.create_index(
        "ix_webhook_dead_letters_source",
        "webhook_dead_letters",
        ["source"],
    )
    op.create_index(
        "ix_webhook_dead_letters_event_id",
        "webhook_dead_letters",
        ["event_id"],
    )
    op.create_index(
        "ix_webhook_dead_letters_event_type",
        "webhook_dead_letters",
        ["event_type"],
    )
    op.create_index(
        "ix_webhook_dead_letters_resolved",
        "webhook_dead_letters",
        ["resolved"],
    )
    op.create_index(
        "ix_webhook_dead_letters_unresolved",
        "webhook_dead_letters",
        ["resolved", "source"],
    )


def downgrade() -> None:
    # Drop webhook_dead_letters table and indexes
    op.drop_index("ix_webhook_dead_letters_unresolved", table_name="webhook_dead_letters")
    op.drop_index("ix_webhook_dead_letters_resolved", table_name="webhook_dead_letters")
    op.drop_index("ix_webhook_dead_letters_event_type", table_name="webhook_dead_letters")
    op.drop_index("ix_webhook_dead_letters_event_id", table_name="webhook_dead_letters")
    op.drop_index("ix_webhook_dead_letters_source", table_name="webhook_dead_letters")
    op.drop_index("ix_webhook_dead_letters_webhook_event_id", table_name="webhook_dead_letters")
    op.drop_table("webhook_dead_letters")

    # Drop webhook_events table and indexes
    op.drop_index("ix_webhook_events_status_type", table_name="webhook_events")
    op.drop_index("ix_webhook_events_retry", table_name="webhook_events")
    op.drop_index("ix_webhook_events_idempotency", table_name="webhook_events")
    op.drop_index("ix_webhook_events_next_retry_at", table_name="webhook_events")
    op.drop_index("ix_webhook_events_order_id", table_name="webhook_events")
    op.drop_index("ix_webhook_events_refund_id", table_name="webhook_events")
    op.drop_index("ix_webhook_events_payment_id", table_name="webhook_events")
    op.drop_index("ix_webhook_events_status", table_name="webhook_events")
    op.drop_index("ix_webhook_events_event_type", table_name="webhook_events")
    op.drop_index("ix_webhook_events_source", table_name="webhook_events")
    op.drop_index("ix_webhook_events_event_id", table_name="webhook_events")
    op.drop_table("webhook_events")
