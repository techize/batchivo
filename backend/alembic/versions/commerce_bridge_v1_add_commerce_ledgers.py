"""Add commerce ledgers without modifying existing manufacturing/customer tables.

Revision ID: commerce_bridge_v1
Revises: data_filament_type_migration
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "commerce_bridge_v1"
down_revision = "data_filament_type_migration"
branch_labels = None
depends_on = None


def identity():
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    # Explicitly new tables. Do not silently adopt unknown existing commerce ledgers.
    op.create_table(
        "commerce_receipts",
        sa.Column("event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("body_sha256", sa.String(64), nullable=False),
        sa.Column("woo_order_id", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        *identity(),
    )
    op.create_index("ix_commerce_receipts_woo_order_id", "commerce_receipts", ["woo_order_id"])
    op.create_table(
        "commerce_orders",
        sa.Column("woo_order_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("batchivo_order_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("effects", postgresql.JSONB(), nullable=False),
        *identity(),
    )
    op.create_index(
        "commerce_orders_payment_unique",
        "commerce_orders",
        [sa.text("(snapshot ->> 'payment_id')")],
        unique=True,
    )
    op.create_table(
        "commerce_fulfilment_events",
        sa.Column("event_id", sa.String(36), nullable=False, unique=True),
        sa.Column("woo_order_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("command_sha256", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        *identity(),
        sa.UniqueConstraint("woo_order_id", "version"),
    )
    op.create_index(
        "ix_commerce_fulfilment_events_woo_order_id", "commerce_fulfilment_events", ["woo_order_id"]
    )
    op.create_index("ix_commerce_fulfilment_events_state", "commerce_fulfilment_events", ["state"])
    op.create_table(
        "commerce_reservations",
        sa.Column("reservation_id", sa.String(36), nullable=False, unique=True),
        sa.Column("woo_order_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        *identity(),
    )
    op.create_index(
        "ix_commerce_reservations_woo_order_id", "commerce_reservations", ["woo_order_id"]
    )
    op.create_index("ix_commerce_reservations_state", "commerce_reservations", ["state"])


def downgrade():
    raise RuntimeError(
        "Retain commerce payment/order ledgers during rollback; destructive downgrade is prohibited"
    )
