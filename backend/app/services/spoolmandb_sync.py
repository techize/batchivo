"""SpoolmanDB synchronisation service.

Fetches filament data from the SpoolmanDB community database
and upserts it into local PostgreSQL tables.

Data source: https://donkie.github.io/SpoolmanDB/
Repository: https://github.com/Donkie/SpoolmanDB
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spoolmandb import SpoolmanDBFilament, SpoolmanDBManufacturer

logger = logging.getLogger(__name__)

# SpoolmanDB data URLs (hosted on GitHub Pages)
SPOOLMANDB_FILAMENTS_URL = "https://donkie.github.io/SpoolmanDB/filaments.json"
SPOOLMANDB_MATERIALS_URL = "https://donkie.github.io/SpoolmanDB/materials.json"


class SpoolmanDBSyncService:
    """Service for syncing data from SpoolmanDB."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def fetch_filaments_data(self) -> list[dict[str, Any]]:
        """Fetch the compiled filaments.json from SpoolmanDB."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SPOOLMANDB_FILAMENTS_URL)
            response.raise_for_status()
            return response.json()

    async def fetch_materials_data(self) -> list[dict[str, Any]]:
        """Fetch the materials.json from SpoolmanDB."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SPOOLMANDB_MATERIALS_URL)
            response.raise_for_status()
            return response.json()

    async def sync(self) -> dict[str, int]:
        """
        Perform full sync from SpoolmanDB.

        Returns dict with counts of added/updated records.
        """
        logger.info("Starting SpoolmanDB sync...")

        # Fetch data from SpoolmanDB
        try:
            filaments_data = await self.fetch_filaments_data()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch SpoolmanDB filaments: {e}")
            raise

        # Track sync statistics
        stats = {
            "manufacturers_added": 0,
            "manufacturers_updated": 0,
            "filaments_added": 0,
            "filaments_updated": 0,
        }

        # Extract unique manufacturers
        manufacturers_seen = set()
        manufacturer_map = {}  # name -> id

        # First pass: collect manufacturers and ensure they exist
        for filament in filaments_data:
            manufacturer_name = filament.get("manufacturer")
            if manufacturer_name and manufacturer_name not in manufacturers_seen:
                manufacturers_seen.add(manufacturer_name)

        # Upsert manufacturers
        for manufacturer_name in manufacturers_seen:
            manufacturer_id, is_new = await self._upsert_manufacturer(manufacturer_name)
            manufacturer_map[manufacturer_name] = manufacturer_id
            if is_new:
                stats["manufacturers_added"] += 1
            else:
                stats["manufacturers_updated"] += 1

        # Now upsert filaments
        for filament in filaments_data:
            manufacturer_name = filament.get("manufacturer")
            manufacturer_id = manufacturer_map.get(manufacturer_name)

            if not manufacturer_id:
                logger.warning(f"Skipping filament with unknown manufacturer: {filament}")
                continue

            is_new = await self._upsert_filament(filament, manufacturer_id)
            if is_new:
                stats["filaments_added"] += 1
            else:
                stats["filaments_updated"] += 1

        await self.db.commit()

        logger.info(
            f"SpoolmanDB sync complete: "
            f"{stats['manufacturers_added']} manufacturers added, "
            f"{stats['manufacturers_updated']} updated, "
            f"{stats['filaments_added']} filaments added, "
            f"{stats['filaments_updated']} updated"
        )

        return stats

    async def _upsert_manufacturer(self, name: str) -> tuple[str, bool]:
        """
        Upsert a manufacturer by name.

        Returns (manufacturer_id, is_new).
        """
        # Check if exists
        result = await self.db.execute(
            select(SpoolmanDBManufacturer).where(SpoolmanDBManufacturer.name == name)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update timestamp
            existing.updated_at = datetime.now(timezone.utc)
            existing.is_active = True
            return str(existing.id), False
        else:
            # Create new
            new_manufacturer = SpoolmanDBManufacturer(
                id=uuid4(),
                name=name,
                is_active=True,
            )
            self.db.add(new_manufacturer)
            await self.db.flush()
            return str(new_manufacturer.id), True

    async def _upsert_filament(self, filament_data: dict[str, Any], manufacturer_id: str) -> bool:
        """
        Upsert a filament record.

        Returns True if new, False if updated.
        """
        external_id = filament_data.get("id")
        if not external_id:
            logger.warning(f"Filament missing id: {filament_data}")
            return False

        # Check if exists
        result = await self.db.execute(
            select(SpoolmanDBFilament).where(SpoolmanDBFilament.external_id == external_id)
        )
        existing = result.scalar_one_or_none()

        # Parse colour hex - handle both single and multi-colour
        # SpoolmanDB uses color_hex for single colour (string) and color_hexes for multi-colour (array)
        color_hex = filament_data.get("color_hex")
        source_color_hexes = filament_data.get("color_hexes")
        color_hexes = None

        if source_color_hexes and isinstance(source_color_hexes, list):
            # Multi-colour filament - convert array to comma-separated string
            color_hexes = ",".join(source_color_hexes)
            # Use first colour as primary if no single color_hex
            if not color_hex and source_color_hexes:
                color_hex = source_color_hexes[0]

        # Cast numeric fields properly
        weight_raw = filament_data.get("weight", 1000)
        weight = int(weight_raw) if weight_raw is not None else 1000
        spool_weight_raw = filament_data.get("spool_weight")
        spool_weight = int(spool_weight_raw) if spool_weight_raw is not None else None

        filament_fields = {
            "external_id": external_id,
            "manufacturer_id": manufacturer_id,
            "name": filament_data.get("name", "Unknown"),
            "material": filament_data.get("material", "Unknown"),
            "density": filament_data.get("density"),
            "diameter": filament_data.get("diameter", 1.75),
            "weight": weight,
            "spool_weight": spool_weight,
            "spool_type": filament_data.get("spool_type"),
            "color_name": filament_data.get("name"),  # Name often includes colour
            "color_hex": color_hex,
            "extruder_temp": filament_data.get("extruder_temp"),
            "bed_temp": filament_data.get("bed_temp"),
            "finish": filament_data.get("finish"),
            "translucent": filament_data.get("translucent", False),
            "glow": filament_data.get("glow", False),
            "pattern": filament_data.get("pattern"),
            "multi_color_direction": filament_data.get("multi_color_direction"),
            "color_hexes": color_hexes,
            "is_active": True,
            "updated_at": datetime.now(timezone.utc),
        }

        if existing:
            # Update existing
            for key, value in filament_fields.items():
                if key != "external_id":  # Don't update the key
                    setattr(existing, key, value)
            return False
        else:
            # Create new
            filament_fields["id"] = uuid4()
            filament_fields["created_at"] = datetime.now(timezone.utc)
            new_filament = SpoolmanDBFilament(**filament_fields)
            self.db.add(new_filament)
            return True

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about the SpoolmanDB data."""
        # Count manufacturers
        manufacturer_count = await self.db.scalar(
            select(func.count()).select_from(SpoolmanDBManufacturer)
        )

        # Count filaments
        filament_count = await self.db.scalar(select(func.count()).select_from(SpoolmanDBFilament))

        # Get unique materials
        materials_result = await self.db.execute(
            select(SpoolmanDBFilament.material).distinct().order_by(SpoolmanDBFilament.material)
        )
        materials = [row[0] for row in materials_result.fetchall()]

        # Get last updated timestamp
        last_updated = await self.db.scalar(select(func.max(SpoolmanDBFilament.updated_at)))

        return {
            "total_manufacturers": manufacturer_count or 0,
            "total_filaments": filament_count or 0,
            "materials": materials,
            "last_sync": last_updated,
        }


async def sync_spoolmandb(db: AsyncSession) -> dict[str, int]:
    """Convenience function to run sync."""
    service = SpoolmanDBSyncService(db)
    return await service.sync()
