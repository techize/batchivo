"""Webhook event model for idempotency tracking and dead-letter queue.

Stores processed webhook events to prevent duplicate processing and
tracks failed events for retry/manual intervention.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.webhook import JSONBType


class WebhookEventStatus(str, Enum):
    """Status of webhook event processing."""

    RECEIVED = "received"  # Event received, not yet processed
    PROCESSING = "processing"  # Currently being processed
    COMPLETED = "completed"  # Successfully processed
    FAILED = "failed"  # Processing failed, will retry
    DEAD_LETTER = "dead_letter"  # Max retries exceeded, needs manual intervention


class WebhookEventSource(str, Enum):
    """Source of the webhook event."""

    SQUARE = "square"
    STRIPE = "stripe"
    PAYPAL = "paypal"


class WebhookEvent(Base, UUIDMixin, TimestampMixin):
    """
    Inbound webhook event for idempotency tracking.

    Each webhook event from Square (or other providers) is recorded here
    to prevent duplicate processing and enable retry logic.
    """

    __tablename__ = "webhook_events"

    # Event identification - unique within source
    event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Unique event ID from the webhook provider",
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=WebhookEventSource.SQUARE.value,
        index=True,
        comment="Webhook source (square, stripe, etc.)",
    )

    # Event type (e.g., payment.created, refund.completed)
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of webhook event",
    )

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WebhookEventStatus.RECEIVED.value,
        index=True,
        comment="Processing status (received, processing, completed, failed, dead_letter)",
    )

    # Full webhook payload
    payload: Mapped[dict] = mapped_column(
        JSONBType,
        nullable=False,
        comment="Full webhook payload as received",
    )

    # Extracted data for quick access
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square payment ID if applicable",
    )

    refund_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square refund ID if applicable",
    )

    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated order ID if found",
    )

    # Retry tracking
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of processing attempts",
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        comment="Maximum number of retry attempts",
    )

    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Scheduled time for next retry",
    )

    # Processing timestamps
    first_received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the event was first received",
    )

    last_processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the event was last processed",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing completed successfully",
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message from last failed attempt",
    )

    error_details: Mapped[Optional[dict]] = mapped_column(
        JSONBType,
        nullable=True,
        comment="Detailed error information (stack trace, context)",
    )

    # Processing result (what was done)
    processing_result: Mapped[Optional[dict]] = mapped_column(
        JSONBType,
        nullable=True,
        comment="Result of successful processing (e.g., order updated)",
    )

    # Signature validation
    signature_valid: Mapped[Optional[bool]] = mapped_column(
        nullable=True,
        comment="Whether webhook signature was valid",
    )

    __table_args__ = (
        # Unique constraint on event_id + source for idempotency
        Index(
            "ix_webhook_events_idempotency",
            "event_id",
            "source",
            unique=True,
        ),
        # Index for finding events to retry
        Index(
            "ix_webhook_events_retry",
            "status",
            "next_retry_at",
        ),
        # Index for monitoring/debugging
        Index(
            "ix_webhook_events_status_type",
            "status",
            "event_type",
        ),
        {"comment": "Inbound webhook events for idempotency and retry handling"},
    )

    def __repr__(self) -> str:
        return f"<WebhookEvent(source={self.source}, event_id={self.event_id[:20]}..., status={self.status})>"


class WebhookDeadLetter(Base, UUIDMixin, TimestampMixin):
    """
    Dead letter record for webhook events that failed permanently.

    Events that exceed max retry attempts are moved here for
    manual investigation and potential reprocessing.
    """

    __tablename__ = "webhook_dead_letters"

    # Reference to original event
    webhook_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("webhook_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Original webhook event that failed",
    )

    # Copy of key fields for easy querying
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Webhook source",
    )

    event_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Original event ID",
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Event type",
    )

    # Failure details
    failure_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Summary of why processing failed",
    )

    total_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total number of attempts made",
    )

    first_failure_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the first failure occurred",
    )

    last_failure_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the last failure occurred",
    )

    # Error history
    error_history: Mapped[Optional[list]] = mapped_column(
        JSONBType,
        nullable=True,
        comment="List of all errors encountered",
    )

    # Resolution tracking
    resolved: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        index=True,
        comment="Whether this has been manually resolved",
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When it was resolved",
    )

    resolved_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Who resolved it (user email or system)",
    )

    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes about how it was resolved",
    )

    __table_args__ = (
        Index("ix_webhook_dead_letters_unresolved", "resolved", "source"),
        {"comment": "Dead letter queue for permanently failed webhook events"},
    )

    def __repr__(self) -> str:
        return f"<WebhookDeadLetter(event_id={self.event_id[:20]}..., resolved={self.resolved})>"
