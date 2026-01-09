"""Add filament properties to spools table

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2024-12-04 23:25:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i6j7k8l9m0n1"
down_revision: Union[str, None] = "h5i6j7k8l9m0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add color_hex column
    op.add_column(
        "spools",
        sa.Column(
            "color_hex",
            sa.String(9),
            nullable=True,
            comment="Hex color code (RGB or RGBA format, e.g., FF5733 or 00FF5733)",
        ),
    )

    # Add diameter column with default 1.75
    op.add_column(
        "spools",
        sa.Column(
            "diameter",
            sa.Numeric(4, 2),
            nullable=False,
            server_default="1.75",
            comment="Filament diameter in mm (typically 1.75 or 2.85)",
        ),
    )

    # Add density column
    op.add_column(
        "spools",
        sa.Column(
            "density",
            sa.Numeric(5, 3),
            nullable=True,
            comment="Filament density in g/cm³ (e.g., 1.24 for PLA)",
        ),
    )

    # Add extruder_temp column
    op.add_column(
        "spools",
        sa.Column(
            "extruder_temp",
            sa.Integer,
            nullable=True,
            comment="Recommended extruder temperature in °C",
        ),
    )

    # Add bed_temp column
    op.add_column(
        "spools",
        sa.Column(
            "bed_temp",
            sa.Integer,
            nullable=True,
            comment="Recommended bed temperature in °C",
        ),
    )

    # Add translucent column
    op.add_column(
        "spools",
        sa.Column(
            "translucent",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="Whether filament is translucent/transparent",
        ),
    )

    # Add glow column
    op.add_column(
        "spools",
        sa.Column(
            "glow",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="Whether filament is glow-in-the-dark",
        ),
    )

    # Add pattern column
    op.add_column(
        "spools",
        sa.Column(
            "pattern",
            sa.String(50),
            nullable=True,
            comment="Pattern type (marble, gradient, speckled, etc.)",
        ),
    )

    # Add spool_type column
    op.add_column(
        "spools",
        sa.Column(
            "spool_type",
            sa.String(50),
            nullable=True,
            comment="Spool type (cardboard, plastic, refill, etc.)",
        ),
    )


def downgrade() -> None:
    op.drop_column("spools", "spool_type")
    op.drop_column("spools", "pattern")
    op.drop_column("spools", "glow")
    op.drop_column("spools", "translucent")
    op.drop_column("spools", "bed_temp")
    op.drop_column("spools", "extruder_temp")
    op.drop_column("spools", "density")
    op.drop_column("spools", "diameter")
    op.drop_column("spools", "color_hex")
