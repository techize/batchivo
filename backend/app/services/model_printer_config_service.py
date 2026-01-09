"""ModelPrinterConfig service for managing printer-specific model settings."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.model_printer_config import ModelPrinterConfig
from app.models.model import Model
from app.models.printer import Printer
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.model_printer_config import (
    ModelPrinterConfigCreate,
    ModelPrinterConfigUpdate,
    ModelPrinterConfigResponse,
    ModelPrinterConfigListResponse,
)

logger = logging.getLogger(__name__)


class ModelPrinterConfigService:
    """Service for managing model-printer configurations."""

    def __init__(self, db: AsyncSession, tenant: Tenant, user: Optional[User] = None):
        """
        Initialize the model printer config service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Current tenant for isolation
            user: Current user performing actions (optional, for audit trail)
        """
        self.db = db
        self.tenant = tenant
        self.user = user

    async def create_config(self, data: ModelPrinterConfigCreate) -> ModelPrinterConfig:
        """
        Create a new model-printer configuration.

        Args:
            data: ModelPrinterConfigCreate schema with config data

        Returns:
            Created ModelPrinterConfig instance

        Raises:
            ValueError: If model or printer doesn't exist or doesn't belong to tenant
        """
        # Verify model exists and belongs to tenant
        model_result = await self.db.execute(
            select(Model).where(Model.id == data.model_id).where(Model.tenant_id == self.tenant.id)
        )
        model = model_result.scalar_one_or_none()
        if not model:
            raise ValueError(f"Model {data.model_id} not found or doesn't belong to tenant")

        # Verify printer exists and belongs to tenant
        printer_result = await self.db.execute(
            select(Printer)
            .where(Printer.id == data.printer_id)
            .where(Printer.tenant_id == self.tenant.id)
        )
        printer = printer_result.scalar_one_or_none()
        if not printer:
            raise ValueError(f"Printer {data.printer_id} not found or doesn't belong to tenant")

        # Check for existing config for this model-printer combination
        existing = await self.get_config_by_model_printer(data.model_id, data.printer_id)
        if existing:
            raise ValueError(
                f"Configuration already exists for model {data.model_id} and printer {data.printer_id}"
            )

        config = ModelPrinterConfig(**data.model_dump())

        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)

        # Load relationships
        await self._load_relationships(config)

        logger.info(
            f"Created config for model '{model.name}' on printer '{printer.name}' "
            f"(id={config.id}, prints_per_plate={config.prints_per_plate})"
        )
        return config

    async def get_config(self, config_id: UUID) -> Optional[ModelPrinterConfig]:
        """
        Get a configuration by ID.

        Args:
            config_id: UUID of the configuration

        Returns:
            ModelPrinterConfig instance or None if not found
        """
        result = await self.db.execute(
            select(ModelPrinterConfig)
            .where(ModelPrinterConfig.id == config_id)
            .options(
                selectinload(ModelPrinterConfig.model),
                selectinload(ModelPrinterConfig.printer),
            )
        )
        config = result.scalar_one_or_none()

        # Verify tenant access through model or printer
        if config:
            if config.model and config.model.tenant_id != self.tenant.id:
                return None
            if config.printer and config.printer.tenant_id != self.tenant.id:
                return None

        return config

    async def get_config_by_model_printer(
        self,
        model_id: UUID,
        printer_id: UUID,
    ) -> Optional[ModelPrinterConfig]:
        """
        Get configuration for a specific model-printer combination.

        Args:
            model_id: UUID of the model
            printer_id: UUID of the printer

        Returns:
            ModelPrinterConfig instance or None if not found
        """
        result = await self.db.execute(
            select(ModelPrinterConfig)
            .where(ModelPrinterConfig.model_id == model_id)
            .where(ModelPrinterConfig.printer_id == printer_id)
            .options(
                selectinload(ModelPrinterConfig.model),
                selectinload(ModelPrinterConfig.printer),
            )
        )
        return result.scalar_one_or_none()

    async def list_configs_for_model(
        self,
        model_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> ModelPrinterConfigListResponse:
        """
        List all configurations for a specific model.

        Args:
            model_id: UUID of the model
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            ModelPrinterConfigListResponse with configs and pagination info
        """
        # Build query joining through model to verify tenant
        query = (
            select(ModelPrinterConfig)
            .join(Model)
            .where(ModelPrinterConfig.model_id == model_id)
            .where(Model.tenant_id == self.tenant.id)
            .options(
                selectinload(ModelPrinterConfig.model),
                selectinload(ModelPrinterConfig.printer),
            )
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        configs = list(result.scalars().all())

        return ModelPrinterConfigListResponse(
            configs=[ModelPrinterConfigResponse.model_validate(c) for c in configs],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def list_configs_for_printer(
        self,
        printer_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> ModelPrinterConfigListResponse:
        """
        List all configurations for a specific printer.

        Args:
            printer_id: UUID of the printer
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            ModelPrinterConfigListResponse with configs and pagination info
        """
        # Build query joining through printer to verify tenant
        query = (
            select(ModelPrinterConfig)
            .join(Printer)
            .where(ModelPrinterConfig.printer_id == printer_id)
            .where(Printer.tenant_id == self.tenant.id)
            .options(
                selectinload(ModelPrinterConfig.model),
                selectinload(ModelPrinterConfig.printer),
            )
        )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        configs = list(result.scalars().all())

        return ModelPrinterConfigListResponse(
            configs=[ModelPrinterConfigResponse.model_validate(c) for c in configs],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def update_config(
        self,
        config_id: UUID,
        data: ModelPrinterConfigUpdate,
    ) -> Optional[ModelPrinterConfig]:
        """
        Update a model-printer configuration.

        Args:
            config_id: UUID of the configuration to update
            data: ModelPrinterConfigUpdate schema with fields to update

        Returns:
            Updated ModelPrinterConfig instance or None if not found
        """
        config = await self.get_config(config_id)
        if not config:
            return None

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)

        await self.db.commit()
        await self.db.refresh(config)

        # Reload relationships
        await self._load_relationships(config)

        logger.info(f"Updated config (id={config.id})")
        return config

    async def delete_config(self, config_id: UUID) -> bool:
        """
        Delete a model-printer configuration.

        Args:
            config_id: UUID of the configuration to delete

        Returns:
            True if deleted, False if not found
        """
        config = await self.get_config(config_id)
        if not config:
            return False

        await self.db.delete(config)
        await self.db.commit()

        logger.info(f"Deleted config (id={config_id})")
        return True

    async def _load_relationships(self, config: ModelPrinterConfig) -> None:
        """Load relationships for a config."""
        result = await self.db.execute(
            select(ModelPrinterConfig)
            .where(ModelPrinterConfig.id == config.id)
            .options(
                selectinload(ModelPrinterConfig.model),
                selectinload(ModelPrinterConfig.printer),
            )
        )
        loaded = result.scalar_one()
        config.model = loaded.model
        config.printer = loaded.printer

    async def get_or_create_config(
        self,
        model_id: UUID,
        printer_id: UUID,
        defaults: Optional[ModelPrinterConfigCreate] = None,
    ) -> tuple[ModelPrinterConfig, bool]:
        """
        Get existing config or create new one if it doesn't exist.

        Args:
            model_id: UUID of the model
            printer_id: UUID of the printer
            defaults: Default values for creation (model_id and printer_id will be overwritten)

        Returns:
            Tuple of (config, created) where created is True if new config was created
        """
        existing = await self.get_config_by_model_printer(model_id, printer_id)
        if existing:
            return existing, False

        # Create new config with defaults or minimal data
        if defaults:
            create_data = ModelPrinterConfigCreate(
                **{**defaults.model_dump(), "model_id": model_id, "printer_id": printer_id}
            )
        else:
            create_data = ModelPrinterConfigCreate(
                model_id=model_id,
                printer_id=printer_id,
            )

        config = await self.create_config(create_data)
        return config, True
