"""add_spoolmandb_tables

Revision ID: g4h5i6j7k8l9
Revises: f3g4h5i6j7k8
Create Date: 2025-12-04 21:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "g4h5i6j7k8l9"
down_revision: Union[str, Sequence[str], None] = "f3g4h5i6j7k8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create SpoolmanDB tables for community filament database."""

    # Create manufacturers table
    op.create_table(
        "spoolmandb_manufacturers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, comment="Manufacturer name"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            default=True,
            comment="Whether active in SpoolmanDB",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_spoolmandb_manufacturers_name", "spoolmandb_manufacturers", ["name"], unique=True
    )

    # Create filaments table
    op.create_table(
        "spoolmandb_filaments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "external_id", sa.String(255), nullable=False, comment="SpoolmanDB unique identifier"
        ),
        sa.Column("manufacturer_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False, comment="Product/colour name"),
        sa.Column(
            "material",
            sa.String(50),
            nullable=False,
            comment="Material type code (PLA, PETG, etc.)",
        ),
        sa.Column("density", sa.Float(), nullable=True, comment="Material density in g/cm³"),
        sa.Column("diameter", sa.Float(), nullable=False, comment="Filament diameter in mm"),
        sa.Column("weight", sa.Integer(), nullable=False, comment="Net filament weight in grams"),
        sa.Column(
            "spool_weight", sa.Integer(), nullable=True, comment="Empty spool weight in grams"
        ),
        sa.Column("spool_type", sa.String(50), nullable=True, comment="Spool material type"),
        sa.Column("color_name", sa.String(100), nullable=True, comment="Colour name"),
        sa.Column("color_hex", sa.String(7), nullable=True, comment="Colour hex code"),
        sa.Column(
            "extruder_temp", sa.Integer(), nullable=True, comment="Recommended extruder temp (°C)"
        ),
        sa.Column("bed_temp", sa.Integer(), nullable=True, comment="Recommended bed temp (°C)"),
        sa.Column("finish", sa.String(50), nullable=True, comment="Surface finish"),
        sa.Column(
            "translucent",
            sa.Boolean(),
            nullable=False,
            default=False,
            comment="Whether translucent",
        ),
        sa.Column(
            "glow", sa.Boolean(), nullable=False, default=False, comment="Whether glows in dark"
        ),
        sa.Column("pattern", sa.String(50), nullable=True, comment="Pattern type"),
        sa.Column(
            "multi_color_direction", sa.String(50), nullable=True, comment="Multi-colour direction"
        ),
        sa.Column(
            "color_hexes",
            sa.Text(),
            nullable=True,
            comment="Comma-separated hex codes for multi-colour",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            default=True,
            comment="Whether active in SpoolmanDB",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["manufacturer_id"], ["spoolmandb_manufacturers.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_spoolmandb_filaments_external_id", "spoolmandb_filaments", ["external_id"], unique=True
    )
    op.create_index(
        "ix_spoolmandb_filaments_manufacturer_id", "spoolmandb_filaments", ["manufacturer_id"]
    )
    op.create_index("ix_spoolmandb_filaments_material", "spoolmandb_filaments", ["material"])
    op.create_index("ix_spoolmandb_filaments_name", "spoolmandb_filaments", ["name"])


def downgrade() -> None:
    """Drop SpoolmanDB tables."""
    op.drop_table("spoolmandb_filaments")
    op.drop_table("spoolmandb_manufacturers")
