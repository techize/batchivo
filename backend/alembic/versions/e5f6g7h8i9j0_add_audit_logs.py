"""add audit logs

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-12-30 10:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: Union[str, None] = "d4e5f6g7h8i9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit action enum
    audit_action_enum = postgresql.ENUM(
        "create",
        "read",
        "update",
        "delete",
        "login",
        "logout",
        "login_failed",
        "password_change",
        "password_reset",
        "order_created",
        "order_status_change",
        "order_refunded",
        "order_cancelled",
        "stock_adjustment",
        "stock_reserved",
        "stock_released",
        "export",
        "import",
        "settings_change",
        "user_invited",
        "user_removed",
        "role_change",
        "customer_registered",
        "customer_verified",
        "review_submitted",
        "review_approved",
        "review_rejected",
        "return_requested",
        "return_approved",
        name="audit_action",
        create_type=False,  # We create it explicitly below with checkfirst=True
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_customer_id", "audit_logs", ["customer_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_tenant_created", "audit_logs", ["tenant_id", "created_at"])
    op.create_index(
        "ix_audit_logs_entity",
        "audit_logs",
        ["tenant_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "ix_audit_logs_user_action",
        "audit_logs",
        ["tenant_id", "user_id", "action"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_audit_logs_user_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_customer_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")

    # Drop table
    op.drop_table("audit_logs")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS audit_action")
