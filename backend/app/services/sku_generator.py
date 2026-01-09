"""SKU generator service for auto-generating sequential SKUs."""

import re
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consumable import ConsumableType
from app.models.model import Model
from app.models.product import Product
from app.models.spool import Spool


class EntityType(str, Enum):
    """Entity types that support SKU generation."""

    PROD = "PROD"  # Products
    MOD = "MOD"  # Models (3D printed parts)
    COM = "COM"  # Consumables
    FIL = "FIL"  # Filament spools
    RUN = "RUN"  # Production runs


# SKU pattern: PREFIX-NNN (e.g., PROD-001, MOD-042)
SKU_PATTERN = re.compile(r"^([A-Z]+)-(\d+)$")


class SKUGeneratorService:
    """Service for generating sequential SKUs for various entity types."""

    # Map entity type to model class and SKU field
    ENTITY_CONFIG = {
        EntityType.PROD: {"model": Product, "field": "sku"},
        EntityType.MOD: {"model": Model, "field": "sku"},
        EntityType.COM: {"model": ConsumableType, "field": "sku"},
        EntityType.FIL: {"model": Spool, "field": "spool_id"},
    }

    @staticmethod
    def parse_sku(sku: str) -> Optional[tuple[str, int]]:
        """
        Parse a SKU into prefix and number.

        Args:
            sku: SKU string (e.g., "PROD-042")

        Returns:
            Tuple of (prefix, number) or None if invalid format
        """
        match = SKU_PATTERN.match(sku)
        if match:
            return match.group(1), int(match.group(2))
        return None

    @staticmethod
    def format_sku(prefix: str, number: int, padding: int = 3) -> str:
        """
        Format a SKU from prefix and number.

        Args:
            prefix: SKU prefix (e.g., "PROD")
            number: SKU number
            padding: Zero-padding width (default 3 -> "001")

        Returns:
            Formatted SKU string (e.g., "PROD-001")
        """
        return f"{prefix}-{str(number).zfill(padding)}"

    @classmethod
    async def get_highest_sku_number(
        cls,
        db: AsyncSession,
        tenant_id: str | UUID,
        entity_type: EntityType,
    ) -> int:
        """
        Get the highest SKU number for an entity type within a tenant.

        Args:
            db: Database session
            tenant_id: Tenant UUID (as string or UUID object)
            entity_type: Type of entity (PROD, MOD, COM, FIL)

        Returns:
            Highest SKU number found, or 0 if none exist
        """
        # Convert string to UUID if needed
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        if entity_type not in cls.ENTITY_CONFIG:
            return 0

        config = cls.ENTITY_CONFIG[entity_type]
        model_class = config["model"]
        field_name = config["field"]
        prefix = entity_type.value

        # Get the SKU field from the model
        sku_field = getattr(model_class, field_name)

        # Query for all SKUs matching the prefix pattern for this tenant
        query = select(sku_field).where(
            model_class.tenant_id == tenant_id,
            sku_field.like(f"{prefix}-%"),
        )

        result = await db.execute(query)
        skus = result.scalars().all()

        # Parse all matching SKUs and find the highest number
        highest = 0
        for sku in skus:
            parsed = cls.parse_sku(sku)
            if parsed and parsed[0] == prefix:
                highest = max(highest, parsed[1])

        return highest

    @classmethod
    async def generate_next_sku(
        cls,
        db: AsyncSession,
        tenant_id: str | UUID,
        entity_type: EntityType,
    ) -> str:
        """
        Generate the next available SKU for an entity type.

        Args:
            db: Database session
            tenant_id: Tenant UUID (as string or UUID object)
            entity_type: Type of entity (PROD, MOD, COM, FIL)

        Returns:
            Next available SKU (e.g., "PROD-001" if none exist, "PROD-043" if 042 is highest)
        """
        highest = await cls.get_highest_sku_number(db, tenant_id, entity_type)
        next_number = highest + 1
        return cls.format_sku(entity_type.value, next_number)

    @classmethod
    async def is_sku_available(
        cls,
        db: AsyncSession,
        tenant_id: str | UUID,
        entity_type: EntityType,
        sku: str,
    ) -> bool:
        """
        Check if a specific SKU is available for use.

        Args:
            db: Database session
            tenant_id: Tenant UUID (as string or UUID object)
            entity_type: Type of entity
            sku: SKU to check

        Returns:
            True if SKU is available, False if already in use
        """
        # Convert string to UUID if needed
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)

        if entity_type not in cls.ENTITY_CONFIG:
            return True

        config = cls.ENTITY_CONFIG[entity_type]
        model_class = config["model"]
        field_name = config["field"]
        sku_field = getattr(model_class, field_name)

        query = select(func.count()).where(
            model_class.tenant_id == tenant_id,
            sku_field == sku,
        )

        result = await db.execute(query)
        count = result.scalar()

        return count == 0
