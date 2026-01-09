"""Webhook subscription and delivery models for outbound webhooks."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeEngine

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class JSONBType(TypeDecorator):
    """
    A JSONB type that falls back to JSON for non-PostgreSQL databases.

    This allows the model to work with both PostgreSQL (for JSONB) and SQLite (for testing).
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB

            return dialect.type_descriptor(JSONB())
        else:
            # Fallback to JSON for SQLite and other databases
            return dialect.type_descriptor(JSON())


if TYPE_CHECKING:
    from app.models.tenant import Tenant


class WebhookEventType(str, Enum):
    """Supported webhook event types."""

    # Order events
    ORDER_CREATED = "order.created"
    ORDER_PAID = "order.paid"
    ORDER_SHIPPED = "order.shipped"
    ORDER_DELIVERED = "order.delivered"
    ORDER_CANCELLED = "order.cancelled"

    # Payment events
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_FAILED = "payment.failed"

    # Inventory events
    INVENTORY_LOW_STOCK = "inventory.low_stock"
    INVENTORY_OUT_OF_STOCK = "inventory.out_of_stock"
    INVENTORY_RESTOCKED = "inventory.restocked"

    # Product events
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    PRODUCT_DELETED = "product.deleted"

    # Review events
    REVIEW_SUBMITTED = "review.submitted"
    REVIEW_APPROVED = "review.approved"

    # Customer events
    CUSTOMER_REGISTERED = "customer.registered"
    CUSTOMER_UPDATED = "customer.updated"

    # Return events
    RETURN_REQUESTED = "return.requested"
    RETURN_APPROVED = "return.approved"
    RETURN_COMPLETED = "return.completed"


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class WebhookSubscription(Base, UUIDMixin, TimestampMixin):
    """
    Webhook subscription for outbound event notifications.

    Tenants can subscribe to events and receive HTTP callbacks
    when those events occur in the system.
    """

    __tablename__ = "webhook_subscriptions"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Webhook configuration
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable name for the webhook",
    )

    url: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
        comment="Target URL for webhook delivery",
    )

    secret: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Secret key for HMAC signature verification",
    )

    # Event subscriptions (stored as JSON array)
    events: Mapped[list] = mapped_column(
        JSONBType,
        nullable=False,
        default=list,
        comment="List of event types to subscribe to",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether webhook is active",
    )

    # Tracking
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Last time webhook was triggered",
    )

    last_success_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Last successful delivery",
    )

    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Consecutive failure count (auto-disable after threshold)",
    )

    # Optional headers (JSON object)
    custom_headers: Mapped[Optional[dict]] = mapped_column(
        JSONBType,
        nullable=True,
        comment="Custom headers to include in webhook requests",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="selectin")
    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        "WebhookDelivery",
        back_populates="subscription",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_webhook_subscriptions_tenant_active", "tenant_id", "is_active"),
        {"comment": "Webhook subscriptions for outbound event notifications"},
    )

    def __repr__(self) -> str:
        return f"<WebhookSubscription(name={self.name}, url={self.url[:50]}...)>"


class WebhookDelivery(Base, UUIDMixin, TimestampMixin):
    """
    Record of a webhook delivery attempt.

    Tracks the payload sent, response received, and delivery status.
    """

    __tablename__ = "webhook_deliveries"

    # Subscription reference
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Webhook subscription that triggered this delivery",
    )

    # Event details
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Event type that triggered the webhook",
    )

    event_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        comment="Unique ID for this event (for idempotency)",
    )

    # Payload
    payload: Mapped[dict] = mapped_column(
        JSONBType,
        nullable=False,
        comment="JSON payload sent to the webhook",
    )

    # Delivery status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DeliveryStatus.PENDING.value,
        index=True,
        comment="Delivery status (pending, success, failed)",
    )

    # Response tracking
    response_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="HTTP response code received",
    )

    response_body: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Response body (truncated if too long)",
    )

    response_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Response time in milliseconds",
    )

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if delivery failed",
    )

    # Retry tracking
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of delivery attempts",
    )

    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="Scheduled time for next retry (if failed)",
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        comment="When delivery was completed (success or final failure)",
    )

    # Relationships
    subscription: Mapped["WebhookSubscription"] = relationship(
        "WebhookSubscription",
        back_populates="deliveries",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_webhook_deliveries_status_retry", "status", "next_retry_at"),
        Index("ix_webhook_deliveries_subscription_created", "subscription_id", "created_at"),
        {"comment": "Webhook delivery attempts and responses"},
    )

    def __repr__(self) -> str:
        return f"<WebhookDelivery(event={self.event_type}, status={self.status})>"
