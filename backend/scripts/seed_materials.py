"""Seed material types reference data."""

import asyncio

from sqlalchemy import select

from app.database import async_session_maker
from app.models.material import MaterialType

# Common 3D printing material types
MATERIALS = [
    {
        "name": "PLA (Polylactic Acid)",
        "code": "PLA",
        "description": "Easy to print, biodegradable, low warp. Best for beginners and decorative prints.",
        "typical_density": 1.24,
        "typical_cost_per_kg": 20.0,
        "min_temp": 190,
        "max_temp": 220,
        "bed_temp": 60,
    },
    {
        "name": "PETG (Polyethylene Terephthalate Glycol)",
        "code": "PETG",
        "description": "Strong, durable, chemical resistant. Good for functional parts.",
        "typical_density": 1.27,
        "typical_cost_per_kg": 25.0,
        "min_temp": 220,
        "max_temp": 250,
        "bed_temp": 80,
    },
    {
        "name": "ABS (Acrylonitrile Butadiene Styrene)",
        "code": "ABS",
        "description": "Strong, heat resistant, post-processable with acetone. Requires enclosure.",
        "typical_density": 1.04,
        "typical_cost_per_kg": 22.0,
        "min_temp": 230,
        "max_temp": 260,
        "bed_temp": 100,
    },
    {
        "name": "TPU (Thermoplastic Polyurethane)",
        "code": "TPU",
        "description": "Flexible, elastic, impact resistant. Great for grips and phone cases.",
        "typical_density": 1.21,
        "typical_cost_per_kg": 35.0,
        "min_temp": 210,
        "max_temp": 240,
        "bed_temp": 60,
    },
    {
        "name": "ASA (Acrylonitrile Styrene Acrylate)",
        "code": "ASA",
        "description": "UV resistant, weather resistant, similar to ABS but better outdoors.",
        "typical_density": 1.07,
        "typical_cost_per_kg": 30.0,
        "min_temp": 240,
        "max_temp": 260,
        "bed_temp": 100,
    },
    {
        "name": "Nylon (Polyamide)",
        "code": "PA",
        "description": "Very strong, durable, abrasion resistant. Absorbs moisture.",
        "typical_density": 1.14,
        "typical_cost_per_kg": 40.0,
        "min_temp": 240,
        "max_temp": 270,
        "bed_temp": 80,
    },
    {
        "name": "Polycarbonate",
        "code": "PC",
        "description": "Extremely strong, heat resistant, impact resistant. Difficult to print.",
        "typical_density": 1.20,
        "typical_cost_per_kg": 45.0,
        "min_temp": 270,
        "max_temp": 310,
        "bed_temp": 110,
    },
]


async def seed_materials():
    """Seed material types into database."""
    async with async_session_maker() as session:
        # Check if materials already exist
        result = await session.execute(select(MaterialType))
        existing = result.scalars().all()

        if existing:
            print(f"✓ Materials already seeded ({len(existing)} materials exist)")
            return

        # Add materials
        for material_data in MATERIALS:
            material = MaterialType(**material_data)
            session.add(material)

        await session.commit()
        print(f"✓ Seeded {len(MATERIALS)} material types")


if __name__ == "__main__":
    print("🌱 Seeding material types...")
    asyncio.run(seed_materials())
    print("✅ Done!")
