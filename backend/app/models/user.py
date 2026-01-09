"""User models for authentication and authorization."""

import uuid
from enum import Enum
from typing import TYPE_CHECKING

import bcrypt
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class UserRole(str, Enum):
    """User roles within a tenant."""

    OWNER = "owner"  # Full access including billing and user management
    ADMIN = "admin"  # Full access except billing
    MEMBER = "member"  # Can create/edit/delete their own data
    VIEWER = "viewer"  # Read-only access


class User(Base, UUIDMixin, TimestampMixin):
    """
    User model representing a person who can access the platform.

    Users authenticate via JWT (email/password).
    A user can belong to multiple tenants with different roles.
    """

    __tablename__ = "users"

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="User email address",
    )

    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Bcrypt hashed password",
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User's full name",
    )

    # Password reset
    reset_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Password reset token",
    )

    reset_token_expires: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Password reset token expiration timestamp (Unix epoch)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether user account is active",
    )

    # Platform administration
    is_platform_admin: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether user has platform-wide admin access",
    )

    # Relationships
    user_tenants: Mapped[list["UserTenant"]] = relationship(
        "UserTenant",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"

    def verify_password(self, plain_password: str) -> bool:
        """Verify a plain password against the hashed password."""
        if not self.hashed_password:
            return False
        return bcrypt.checkpw(plain_password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    def set_password(self, plain_password: str) -> None:
        """Hash and set the user's password."""
        # bcrypt automatically handles the 72-byte limitation
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        self.hashed_password = hashed.decode("utf-8")


class UserTenant(Base, UUIDMixin, TimestampMixin):
    """
    Join table linking users to tenants with roles.

    Represents a user's membership in a tenant with a specific role.
    """

    __tablename__ = "user_tenants"

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role within this tenant
    role: Mapped[UserRole] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.MEMBER,
        comment="User's role within this tenant",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_tenants")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="user_tenants")

    # Constraints
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
        {"comment": "User-Tenant relationship with roles"},
    )

    def __repr__(self) -> str:
        return (
            f"<UserTenant(user_id={self.user_id}, tenant_id={self.tenant_id}, role='{self.role}')>"
        )
