"""Email verification token model for user registration."""

import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class VerificationTokenType(str, Enum):
    """Types of verification tokens."""

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    TENANT_INVITE = "tenant_invite"


class EmailVerificationToken(Base, UUIDMixin, TimestampMixin):
    """
    Email verification token for user registration and password reset.

    Tokens are:
    - Single-use (deleted after successful verification)
    - Time-limited (default 24 hours for email, 1 hour for password reset)
    - Cryptographically secure (64-character random string)
    """

    __tablename__ = "email_verification_tokens"

    # Token details
    token: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
        comment="Cryptographically secure verification token",
    )

    token_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=VerificationTokenType.EMAIL_VERIFICATION.value,
        comment="Type of token (email_verification, password_reset, tenant_invite)",
    )

    # Associated email (for pre-registration verification)
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Email address this token is for",
    )

    # Registration data (stored as JSON until verification)
    registration_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON-encoded registration data (for pending registrations)",
    )

    # Token expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Token expiration timestamp",
    )

    # Usage tracking
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the token was used (if used)",
    )

    @classmethod
    def generate_token(cls) -> str:
        """Generate a cryptographically secure token."""
        return secrets.token_urlsafe(48)  # 64 characters

    @classmethod
    def create_email_verification(
        cls,
        email: str,
        registration_data: str | None = None,
        expires_hours: int = 24,
    ) -> "EmailVerificationToken":
        """
        Create an email verification token.

        Args:
            email: Email address to verify
            registration_data: Optional JSON registration data
            expires_hours: Hours until token expires

        Returns:
            New EmailVerificationToken instance
        """
        return cls(
            token=cls.generate_token(),
            token_type=VerificationTokenType.EMAIL_VERIFICATION.value,
            email=email.lower(),
            registration_data=registration_data,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
        )

    @classmethod
    def create_password_reset(
        cls,
        email: str,
        expires_hours: int = 1,
    ) -> "EmailVerificationToken":
        """
        Create a password reset token.

        Args:
            email: Email address for password reset
            expires_hours: Hours until token expires

        Returns:
            New EmailVerificationToken instance
        """
        return cls(
            token=cls.generate_token(),
            token_type=VerificationTokenType.PASSWORD_RESET.value,
            email=email.lower(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_hours),
        )

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used(self) -> bool:
        """Check if token has been used."""
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if token is still valid (not expired and not used)."""
        return not self.is_expired and not self.is_used

    def mark_as_used(self) -> None:
        """Mark the token as used."""
        self.used_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            f"<EmailVerificationToken(id={self.id}, "
            f"email='{self.email}', type='{self.token_type}', "
            f"expired={self.is_expired}, used={self.is_used})>"
        )
