"""add_printers_table

Revision ID: 43cc1df327c1
Revises: r5s6t7u8v9w0
Create Date: 2025-12-15 13:28:01.673897

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "43cc1df327c1"
down_revision: Union[str, Sequence[str], None] = "r5s6t7u8v9w0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create printers table
    op.create_table(
        "printers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
            comment='Printer name (e.g., "Bambu A1 Mini")',
        ),
        sa.Column(
            "manufacturer", sa.String(length=100), nullable=True, comment="Manufacturer name"
        ),
        sa.Column("model", sa.String(length=100), nullable=True, comment="Model name"),
        sa.Column(
            "bed_size_x_mm", sa.Integer(), nullable=True, comment="Bed size X in millimeters"
        ),
        sa.Column(
            "bed_size_y_mm", sa.Integer(), nullable=True, comment="Bed size Y in millimeters"
        ),
        sa.Column(
            "bed_size_z_mm", sa.Integer(), nullable=True, comment="Bed size Z in millimeters"
        ),
        sa.Column(
            "nozzle_diameter_mm",
            sa.Numeric(precision=3, scale=2),
            nullable=True,
            server_default="0.4",
            comment="Nozzle diameter in millimeters",
        ),
        sa.Column(
            "default_bed_temp", sa.Integer(), nullable=True, comment="Default bed temperature"
        ),
        sa.Column(
            "default_nozzle_temp", sa.Integer(), nullable=True, comment="Default nozzle temperature"
        ),
        sa.Column(
            "capabilities",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
            comment="Printer capabilities (AMS, materials, etc.)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether printer is active",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_printer_tenant_name"),
        comment="3D printers available for production runs",
    )

    # Create indexes
    op.create_index("idx_printers_tenant", "printers", ["tenant_id"])
    op.create_index("idx_printers_active", "printers", ["is_active"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_printers_active", table_name="printers")
    op.drop_index("idx_printers_tenant", table_name="printers")

    # Drop table
    op.drop_table("printers")
