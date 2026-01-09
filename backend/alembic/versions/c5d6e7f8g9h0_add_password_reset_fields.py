"""Add password reset fields to users table

Revision ID: c5d6e7f8g9h0
Revises: b4f5c6d7e8f9
Create Date: 2025-11-18 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8g9h0"
down_revision: Union[str, Sequence[str], None] = "b4f5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password reset token and expiration fields to users table."""
    # Add reset_token column
    op.add_column(
        "users",
        sa.Column(
            "reset_token", sa.String(length=255), nullable=True, comment="Password reset token"
        ),
    )

    # Add reset_token_expires column
    op.add_column(
        "users",
        sa.Column(
            "reset_token_expires",
            sa.Integer(),
            nullable=True,
            comment="Password reset token expiration timestamp (Unix epoch)",
        ),
    )


def downgrade() -> None:
    """Remove password reset fields from users table."""
    # Remove the columns
    op.drop_column("users", "reset_token_expires")
    op.drop_column("users", "reset_token")
