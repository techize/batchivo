"""Payment log model for auditing payment operations."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, DateTime, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class PaymentLogStatus:
    """Payment log status constants."""

    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class PaymentLogOperation:
    """Payment log operation types."""

    PAYMENT = "payment"
    REFUND = "refund"
    WEBHOOK = "webhook"
    STATUS_CHECK = "status_check"


class PaymentLog(Base, UUIDMixin, TimestampMixin):
    """
    PaymentLog records all payment-related operations for auditing.

    Tracks payment attempts, refunds, webhooks, and status checks
    with full request/response data for debugging and reconciliation.
    """

    __tablename__ = "payment_logs"

    # Optional order reference (may not exist for failed payments)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Associated order ID if available",
    )

    # Order number for easier correlation (even if order creation failed)
    order_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Order number used as idempotency key",
    )

    # Payment provider info
    payment_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="square",
        comment="Payment provider (square, stripe, etc.)",
    )

    # Square transaction IDs
    payment_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square payment ID",
    )
    refund_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Square refund ID (for refund operations)",
    )

    # Operation details
    operation: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PaymentLogOperation.PAYMENT,
        index=True,
        comment="Operation type: payment, refund, webhook, status_check",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PaymentLogStatus.INITIATED,
        index=True,
        comment="Operation status: initiated, success, failed, retrying",
    )

    # Amount info
    amount: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Amount in smallest currency unit (pence)",
    )
    currency: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        default="GBP",
        comment="Currency code",
    )

    # Request/Response data (stored as JSON for flexibility)
    request_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Request data sent to payment provider (sensitive data redacted)",
    )
    response_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Response data from payment provider",
    )

    # Error details
    error_code: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Error code from payment provider",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable error message",
    )

    # Retry tracking
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Attempt number (1 for first try, 2+ for retries)",
    )

    # Idempotency key used
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Idempotency key used for this operation",
    )

    # Customer info (for correlation)
    customer_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Customer email for correlation",
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the operation started",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the operation completed (success or failure)",
    )

    # IP and user agent (for fraud detection)
    client_ip: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
        comment="Client IP address",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Client user agent string",
    )
