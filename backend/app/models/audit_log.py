"""Audit log model for tracking user actions."""

import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"

    # Order lifecycle
    ORDER_CREATED = "order_created"
    ORDER_STATUS_CHANGE = "order_status_change"
    ORDER_REFUNDED = "order_refunded"
    ORDER_CANCELLED = "order_cancelled"

    # Inventory
    STOCK_ADJUSTMENT = "stock_adjustment"
    STOCK_RESERVED = "stock_reserved"
    STOCK_RELEASED = "stock_released"

    # Admin actions
    EXPORT = "export"
    IMPORT = "import"
    SETTINGS_CHANGE = "settings_change"
    USER_INVITED = "user_invited"
    USER_REMOVED = "user_removed"
    ROLE_CHANGE = "role_change"

    # Customer actions
    CUSTOMER_REGISTERED = "customer_registered"
    CUSTOMER_VERIFIED = "customer_verified"
    REVIEW_SUBMITTED = "review_submitted"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    RETURN_REQUESTED = "return_requested"
    RETURN_APPROVED = "return_approved"


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """
    Audit log entry for tracking user actions.

    Records who did what, when, and what changed for compliance and debugging.
    """

    __tablename__ = "audit_logs"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Who performed the action
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # What action was performed
    action: Mapped[AuditAction] = mapped_column(
        SQLEnum(AuditAction, name="audit_action", create_constraint=True),
        nullable=False,
        index=True,
    )

    # What entity was affected
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        nullable=True,
        index=True,
    )

    # What changed (for UPDATE actions)
    # Format: {"field_name": {"old": old_value, "new": new_value}}
    changes: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Additional context (API endpoint, request ID, etc.)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    # Description of the action (human-readable)
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    customer = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")

    __table_args__ = (
        # Index for common query patterns
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_logs_entity", "tenant_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_user_action", "tenant_id", "user_id", "action"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(action={self.action.value}, "
            f"entity={self.entity_type}:{self.entity_id})>"
        )
