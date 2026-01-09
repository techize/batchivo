"""Seed common material types

Revision ID: d1e2f3g4h5i6
Revises: c5d6e7f8g9h0
Create Date: 2025-11-18 13:00:00.000000

"""

from typing import Sequence, Union
from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d1e2f3g4h5i6"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8g9h0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed common 3D printing material types."""

    # Check if materials already exist - if so, skip seeding
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM material_types WHERE code IN ('PLA', 'PETG', 'ABS', 'TPU')")
    )
    count = result.scalar()

    if count > 0:
        # Materials already seeded, skip
        return

    # Define common material types with their properties
    materials = [
        {
            "id": str(uuid.uuid4()),
            "code": "PLA",
            "name": "Polylactic Acid (PLA)",
            "description": "Easy to print, biodegradable, good for beginners. Low warping, wide color selection.",
            "typical_density": 1.24,
            "typical_cost_per_kg": 20.0,
            "min_temp": 190,
            "max_temp": 220,
            "bed_temp": 60,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "id": str(uuid.uuid4()),
            "code": "PETG",
            "name": "Polyethylene Terephthalate Glycol (PETG)",
            "description": "Strong, durable, good chemical resistance. Easy to print, food-safe options available.",
            "typical_density": 1.27,
            "typical_cost_per_kg": 25.0,
            "min_temp": 220,
            "max_temp": 250,
            "bed_temp": 80,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "id": str(uuid.uuid4()),
            "code": "ABS",
            "name": "Acrylonitrile Butadiene Styrene (ABS)",
            "description": "Strong, heat-resistant, good for functional parts. Requires heated bed and enclosure.",
            "typical_density": 1.04,
            "typical_cost_per_kg": 22.0,
            "min_temp": 220,
            "max_temp": 250,
            "bed_temp": 100,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "id": str(uuid.uuid4()),
            "code": "TPU",
            "name": "Thermoplastic Polyurethane (TPU)",
            "description": "Flexible, elastic, shock-absorbing. Great for phone cases, seals, and wearables.",
            "typical_density": 1.21,
            "typical_cost_per_kg": 35.0,
            "min_temp": 220,
            "max_temp": 250,
            "bed_temp": 60,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "id": str(uuid.uuid4()),
            "code": "ASA",
            "name": "Acrylonitrile Styrene Acrylate (ASA)",
            "description": "UV-resistant, weather-resistant, similar to ABS. Great for outdoor applications.",
            "typical_density": 1.07,
            "typical_cost_per_kg": 30.0,
            "min_temp": 240,
            "max_temp": 260,
            "bed_temp": 100,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "id": str(uuid.uuid4()),
            "code": "NYLON",
            "name": "Nylon (Polyamide)",
            "description": "Very strong, flexible, wear-resistant. Hygroscopic (absorbs moisture).",
            "typical_density": 1.14,
            "typical_cost_per_kg": 40.0,
            "min_temp": 240,
            "max_temp": 260,
            "bed_temp": 80,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "id": str(uuid.uuid4()),
            "code": "PCTG",
            "name": "Polycyclohexylene Terephthalate Glycol (PCTG)",
            "description": "Similar to PETG but more impact resistant. Food-safe, clear prints possible.",
            "typical_density": 1.23,
            "typical_cost_per_kg": 28.0,
            "min_temp": 230,
            "max_temp": 260,
            "bed_temp": 80,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
        {
            "id": str(uuid.uuid4()),
            "code": "PC",
            "name": "Polycarbonate (PC)",
            "description": "Very strong, heat-resistant, transparent. Difficult to print, requires high temps.",
            "typical_density": 1.20,
            "typical_cost_per_kg": 45.0,
            "min_temp": 270,
            "max_temp": 310,
            "bed_temp": 110,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        },
    ]

    # Insert materials into table
    op.bulk_insert(
        sa.table(
            "material_types",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("code", sa.String),
            sa.column("name", sa.String),
            sa.column("description", sa.Text),
            sa.column("typical_density", sa.Float),
            sa.column("typical_cost_per_kg", sa.Float),
            sa.column("min_temp", sa.Integer),
            sa.column("max_temp", sa.Integer),
            sa.column("bed_temp", sa.Integer),
            sa.column("is_active", sa.Boolean),
            sa.column("created_at", sa.DateTime(timezone=True)),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        materials,
    )


def downgrade() -> None:
    """Remove seeded material types."""
    op.execute(
        """
        DELETE FROM material_types
        WHERE code IN ('PLA', 'PETG', 'ABS', 'TPU', 'ASA', 'NYLON', 'PCTG', 'PC')
        """
    )
