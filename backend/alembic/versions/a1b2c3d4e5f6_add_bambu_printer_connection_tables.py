"""add_bambu_printer_connection_tables

Revision ID: a1b2c3d4e5f6
Revises: e8bd61b68b58
Create Date: 2025-12-17 13:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e8bd61b68b58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create printer_connections table
    op.create_table(
        "printer_connections",
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            nullable=False,
            comment="Tenant ID for multi-tenant isolation",
        ),
        sa.Column(
            "printer_id",
            sa.Uuid(),
            nullable=False,
            comment="Associated printer ID",
        ),
        sa.Column(
            "connection_type",
            sa.String(length=50),
            nullable=False,
            server_default="manual",
            comment="Connection type (bambu_lan, bambu_cloud, octoprint, klipper, manual)",
        ),
        sa.Column(
            "serial_number",
            sa.String(length=50),
            nullable=True,
            comment="Bambu printer serial number (from printer screen)",
        ),
        sa.Column(
            "ip_address",
            sa.String(length=45),
            nullable=True,
            comment="Printer IP address (for LAN connections)",
        ),
        sa.Column(
            "port",
            sa.Integer(),
            nullable=False,
            server_default="8883",
            comment="Connection port (default 8883 for Bambu MQTT)",
        ),
        sa.Column(
            "access_code",
            sa.String(length=100),
            nullable=True,
            comment="LAN access code (from Bambu printer settings)",
        ),
        sa.Column(
            "cloud_username",
            sa.String(length=100),
            nullable=True,
            comment="Cloud account username/user_id (for cloud connections)",
        ),
        sa.Column(
            "cloud_token",
            sa.Text(),
            nullable=True,
            comment="Cloud access token (for cloud connections)",
        ),
        sa.Column(
            "ams_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of AMS units connected (0-4)",
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether connection is enabled",
        ),
        sa.Column(
            "is_connected",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Current connection status (runtime)",
        ),
        sa.Column(
            "last_connected_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last successful connection timestamp",
        ),
        sa.Column(
            "last_status_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last status message received timestamp",
        ),
        sa.Column(
            "connection_error",
            sa.Text(),
            nullable=True,
            comment="Last connection error message",
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["printer_id"], ["printers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("printer_id", name="uq_printer_connection_printer"),
        comment="Printer connection configurations for integrations",
    )
    op.create_index(
        op.f("ix_printer_connections_tenant_id"),
        "printer_connections",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_printer_connections_printer_id"),
        "printer_connections",
        ["printer_id"],
        unique=False,
    )

    # Create ams_slot_mappings table
    op.create_table(
        "ams_slot_mappings",
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            nullable=False,
            comment="Tenant ID for multi-tenant isolation",
        ),
        sa.Column(
            "printer_id",
            sa.Uuid(),
            nullable=False,
            comment="Associated printer ID",
        ),
        sa.Column(
            "ams_id",
            sa.Integer(),
            nullable=False,
            comment="AMS unit index (0-3 for up to 4 daisy-chained units)",
        ),
        sa.Column(
            "tray_id",
            sa.Integer(),
            nullable=False,
            comment="Tray/slot index within AMS unit (0-3)",
        ),
        sa.Column(
            "spool_id",
            sa.Uuid(),
            nullable=True,
            comment="Mapped Nozzly spool ID (null if unmapped)",
        ),
        sa.Column(
            "rfid_tag_uid",
            sa.String(length=32),
            nullable=True,
            comment="RFID tag UID from AMS (for Bambu filament)",
        ),
        sa.Column(
            "last_reported_type",
            sa.String(length=20),
            nullable=True,
            comment="Last reported filament type from AMS (e.g., PLA, PETG)",
        ),
        sa.Column(
            "last_reported_color",
            sa.String(length=9),
            nullable=True,
            comment="Last reported color from AMS (RRGGBBAA hex)",
        ),
        sa.Column(
            "last_reported_remain",
            sa.Integer(),
            nullable=True,
            comment="Last reported remaining percentage from AMS (0-100)",
        ),
        sa.Column(
            "last_reported_temp_min",
            sa.Integer(),
            nullable=True,
            comment="Last reported min nozzle temp from AMS",
        ),
        sa.Column(
            "last_reported_temp_max",
            sa.Integer(),
            nullable=True,
            comment="Last reported max nozzle temp from AMS",
        ),
        sa.Column(
            "is_auto_mapped",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether mapping was auto-created via RFID match",
        ),
        sa.Column(
            "has_filament",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether AMS reports filament in this slot",
        ),
        sa.Column(
            "is_bambu_filament",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether filament has valid Bambu RFID tag",
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time spool was synced from AMS data",
        ),
        sa.Column(
            "last_status_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last time AMS status was received for this slot",
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["printer_id"], ["printers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spool_id"], ["spools.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("printer_id", "ams_id", "tray_id", name="uq_ams_slot_printer_ams_tray"),
        comment="AMS slot to spool mappings for Bambu printers",
    )
    op.create_index(
        op.f("ix_ams_slot_mappings_tenant_id"),
        "ams_slot_mappings",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ams_slot_mappings_printer_id"),
        "ams_slot_mappings",
        ["printer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ams_slot_mappings_spool_id"),
        "ams_slot_mappings",
        ["spool_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ams_slot_mappings_rfid_tag_uid"),
        "ams_slot_mappings",
        ["rfid_tag_uid"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop ams_slot_mappings table
    op.drop_index(op.f("ix_ams_slot_mappings_rfid_tag_uid"), table_name="ams_slot_mappings")
    op.drop_index(op.f("ix_ams_slot_mappings_spool_id"), table_name="ams_slot_mappings")
    op.drop_index(op.f("ix_ams_slot_mappings_printer_id"), table_name="ams_slot_mappings")
    op.drop_index(op.f("ix_ams_slot_mappings_tenant_id"), table_name="ams_slot_mappings")
    op.drop_table("ams_slot_mappings")

    # Drop printer_connections table
    op.drop_index(op.f("ix_printer_connections_printer_id"), table_name="printer_connections")
    op.drop_index(op.f("ix_printer_connections_tenant_id"), table_name="printer_connections")
    op.drop_table("printer_connections")
