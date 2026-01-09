"""create_email_verification_tokens_table

Revision ID: 7399942463dd
Revises: 07badcd78841
Create Date: 2025-12-30 13:41:52.034817

This migration creates the email_verification_tokens table for:
- User registration email verification
- Password reset tokens
- Tenant invitation tokens

Tokens are single-use, time-limited, and cryptographically secure.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7399942463dd"
down_revision: Union[str, Sequence[str], None] = "07badcd78841"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create email_verification_tokens table."""
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "token",
            sa.String(128),
            nullable=False,
            comment="Cryptographically secure verification token",
        ),
        sa.Column(
            "token_type",
            sa.String(50),
            nullable=False,
            server_default="email_verification",
            comment="Type of token (email_verification, password_reset, tenant_invite)",
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=False,
            comment="Email address this token is for",
        ),
        sa.Column(
            "registration_data",
            sa.Text(),
            nullable=True,
            comment="JSON-encoded registration data (for pending registrations)",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Token expiration timestamp",
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the token was used (if used)",
        ),
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
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient lookups
    op.create_index(
        "ix_email_verification_tokens_token",
        "email_verification_tokens",
        ["token"],
        unique=True,
    )
    op.create_index(
        "ix_email_verification_tokens_email",
        "email_verification_tokens",
        ["email"],
    )
    op.create_index(
        "ix_email_verification_tokens_type_email",
        "email_verification_tokens",
        ["token_type", "email"],
    )


def downgrade() -> None:
    """Drop email_verification_tokens table."""
    op.drop_index(
        "ix_email_verification_tokens_type_email",
        table_name="email_verification_tokens",
    )
    op.drop_index(
        "ix_email_verification_tokens_email",
        table_name="email_verification_tokens",
    )
    op.drop_index(
        "ix_email_verification_tokens_token",
        table_name="email_verification_tokens",
    )
    op.drop_table("email_verification_tokens")
