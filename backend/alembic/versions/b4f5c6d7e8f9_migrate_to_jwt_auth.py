"""Migrate to JWT auth - add hashed_password, remove authentik_user_id

Revision ID: b4f5c6d7e8f9
Revises: f3a4b8c9d21e
Create Date: 2025-11-18 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4f5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "a8d3e5f7g9h1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate users table from Authentik to JWT auth."""
    # Drop the authentik_user_id index and column
    op.drop_index("ix_users_authentik_user_id", table_name="users")
    op.drop_column("users", "authentik_user_id")

    # Add hashed_password column
    op.add_column(
        "users",
        sa.Column(
            "hashed_password",
            sa.String(length=255),
            nullable=True,
            comment="Bcrypt hashed password",
        ),
    )

    # Note: nullable=True temporarily because existing users won't have passwords
    # In production, you'd need a data migration step here


def downgrade() -> None:
    """Revert to Authentik auth."""
    # Remove hashed_password
    op.drop_column("users", "hashed_password")

    # Re-add authentik_user_id
    op.add_column(
        "users",
        sa.Column(
            "authentik_user_id",
            sa.String(length=255),
            nullable=True,
            comment="Authentik user ID (from OIDC 'sub' claim)",
        ),
    )
    op.create_index("ix_users_authentik_user_id", "users", ["authentik_user_id"], unique=True)
