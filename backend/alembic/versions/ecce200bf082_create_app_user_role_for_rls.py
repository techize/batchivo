"""create_app_user_role_for_rls

Revision ID: ecce200bf082
Revises: g7h8i9j0k1l2
Create Date: 2025-12-30 13:07:31.304464

This migration creates the app_user PostgreSQL role for Row-Level Security (RLS).
The app_user role has limited privileges (no superuser) and is used by the
application to connect to the database when RLS is enabled.

RLS policies will use the session variable app.current_tenant_id to filter data.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "ecce200bf082"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create app_user role for RLS and grant necessary permissions.

    The app_user role:
    - Has LOGIN privilege (can connect)
    - Does NOT have SUPERUSER (RLS policies are enforced)
    - Can SELECT, INSERT, UPDATE, DELETE on all tables
    - Can use sequences (for auto-increment IDs)

    Note: The password 'PLACEHOLDER_CHANGE_ME' must be changed in production
    via: ALTER ROLE app_user WITH PASSWORD 'secure_password';
    """
    connection = op.get_bind()

    # Check if role already exists (idempotent)
    result = connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'app_user'"))
    role_exists = result.fetchone() is not None

    if not role_exists:
        # Create the app_user role with LOGIN but without SUPERUSER
        # Password should be changed in production via ALTER ROLE
        op.execute(
            text("""
            CREATE ROLE app_user WITH
                LOGIN
                PASSWORD 'PLACEHOLDER_CHANGE_ME'
                NOSUPERUSER
                NOCREATEDB
                NOCREATEROLE
                INHERIT
        """)
        )

    # Get current database name
    db_result = connection.execute(text("SELECT current_database()"))
    db_name = db_result.fetchone()[0]

    # Grant CONNECT on the database
    # Note: Using f-string here is safe as db_name comes from database itself
    op.execute(text(f"GRANT CONNECT ON DATABASE {db_name} TO app_user"))

    # Grant USAGE on the public schema
    op.execute(text("GRANT USAGE ON SCHEMA public TO app_user"))

    # Grant SELECT, INSERT, UPDATE, DELETE on ALL existing tables
    op.execute(
        text("""
        GRANT SELECT, INSERT, UPDATE, DELETE
        ON ALL TABLES IN SCHEMA public
        TO app_user
    """)
    )

    # Grant USAGE on all sequences (for auto-increment IDs)
    op.execute(
        text("""
        GRANT USAGE, SELECT
        ON ALL SEQUENCES IN SCHEMA public
        TO app_user
    """)
    )

    # Set default privileges for FUTURE tables created by the owner
    # This ensures app_user can access tables created by migrations
    op.execute(
        text("""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user
    """)
    )

    op.execute(
        text("""
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO app_user
    """)
    )


def downgrade() -> None:
    """
    Remove app_user role and revoke all permissions.

    Note: This will fail if there are active connections using app_user.
    Terminate connections first: SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = 'app_user';
    """
    connection = op.get_bind()

    # Check if role exists
    result = connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'app_user'"))
    role_exists = result.fetchone() is not None

    if role_exists:
        # Revoke default privileges
        op.execute(
            text("""
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user
        """)
        )

        op.execute(
            text("""
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
            REVOKE USAGE, SELECT ON SEQUENCES FROM app_user
        """)
        )

        # Revoke privileges on existing objects
        op.execute(
            text("""
            REVOKE SELECT, INSERT, UPDATE, DELETE
            ON ALL TABLES IN SCHEMA public
            FROM app_user
        """)
        )

        op.execute(
            text("""
            REVOKE USAGE, SELECT
            ON ALL SEQUENCES IN SCHEMA public
            FROM app_user
        """)
        )

        # Revoke schema usage
        op.execute(text("REVOKE USAGE ON SCHEMA public FROM app_user"))

        # Get current database name and revoke connect
        db_result = connection.execute(text("SELECT current_database()"))
        db_name = db_result.fetchone()[0]
        op.execute(text(f"REVOKE CONNECT ON DATABASE {db_name} FROM app_user"))

        # Drop the role
        op.execute(text("DROP ROLE app_user"))
