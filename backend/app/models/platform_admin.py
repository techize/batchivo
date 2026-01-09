"""Platform admin models for audit logging and settings."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class PlatformAdminAuditLog(Base, UUIDMixin):
    """
    Audit log for tracking platform admin actions.

    Records all actions taken by platform admins for security
    and compliance purposes.
    """

    __tablename__ = "platform_admin_audit_logs"

    # Who performed the action
    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the platform admin who performed the action",
    )

    # What action was performed
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Action type: impersonate, deactivate_tenant, reactivate_tenant, update_setting, etc.",
    )

    # Target of the action
    target_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of target: tenant, user, setting",
    )

    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="ID of the target entity",
    )

    # Additional context
    action_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional context about the action",
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # Supports IPv6
        nullable=True,
        comment="IP address of the admin when action was performed",
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User agent string of the admin's browser",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
        default=datetime.utcnow,
        comment="When the action was performed",
    )

    # Relationships
    admin_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[admin_user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<PlatformAdminAuditLog(id={self.id}, action='{self.action}', "
            f"admin_user_id={self.admin_user_id})>"
        )


class PlatformSetting(Base):
    """
    Platform-wide configuration settings.

    Key-value store for global platform configuration that applies
    across all tenants.
    """

    __tablename__ = "platform_settings"

    # Primary key is the setting key
    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="Unique setting identifier",
    )

    # Value stored as JSON for flexibility
    value: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Setting value (JSON)",
    )

    # Documentation
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of the setting",
    )

    # Audit fields
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="When the setting was last updated",
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID of the admin who last updated this setting",
    )

    # Relationships
    updated_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[updated_by],
    )

    def __repr__(self) -> str:
        return f"<PlatformSetting(key='{self.key}')>"
