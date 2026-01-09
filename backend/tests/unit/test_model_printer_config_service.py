"""Unit tests for ModelPrinterConfigService."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.model_printer_config import (
    ModelPrinterConfigCreate,
    ModelPrinterConfigUpdate,
)
from app.services.model_printer_config_service import ModelPrinterConfigService


class TestModelPrinterConfigServiceCreate:
    """Tests for configuration creation."""

    @pytest.mark.asyncio
    async def test_create_config_basic(self, db_session, test_tenant, test_model, test_printer):
        """Test creating a basic model-printer configuration."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        data = ModelPrinterConfigCreate(
            model_id=test_model.id,
            printer_id=test_printer.id,
        )

        config = await service.create_config(data)

        assert config.id is not None
        assert config.model_id == test_model.id
        assert config.printer_id == test_printer.id

    @pytest.mark.asyncio
    async def test_create_config_full_details(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test creating a configuration with all fields."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        data = ModelPrinterConfigCreate(
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=4,
            print_time_minutes=60,
            material_weight_grams=Decimal("45.5"),
            bed_temperature=65,
            nozzle_temperature=215,
            layer_height=Decimal("0.16"),
            infill_percentage=20,
            supports=True,
            brim=False,
            notes="Test configuration notes",
        )

        config = await service.create_config(data)

        assert config.prints_per_plate == 4
        assert config.print_time_minutes == 60
        assert config.material_weight_grams == Decimal("45.5")
        assert config.bed_temperature == 65
        assert config.nozzle_temperature == 215
        assert config.layer_height == Decimal("0.16")
        assert config.infill_percentage == 20
        assert config.supports is True
        assert config.brim is False
        assert config.notes == "Test configuration notes"

    @pytest.mark.asyncio
    async def test_create_config_invalid_model(self, db_session, test_tenant, test_printer):
        """Test creating config with non-existent model raises error."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        data = ModelPrinterConfigCreate(
            model_id=uuid4(),  # Non-existent model
            printer_id=test_printer.id,
        )

        with pytest.raises(ValueError, match="Model.*not found"):
            await service.create_config(data)

    @pytest.mark.asyncio
    async def test_create_config_invalid_printer(self, db_session, test_tenant, test_model):
        """Test creating config with non-existent printer raises error."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        data = ModelPrinterConfigCreate(
            model_id=test_model.id,
            printer_id=uuid4(),  # Non-existent printer
        )

        with pytest.raises(ValueError, match="Printer.*not found"):
            await service.create_config(data)

    @pytest.mark.asyncio
    async def test_create_config_duplicate_raises_error(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test creating duplicate config raises error."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        data = ModelPrinterConfigCreate(
            model_id=test_model.id,
            printer_id=test_printer.id,
        )

        # Create first config
        await service.create_config(data)

        # Try to create duplicate
        with pytest.raises(ValueError, match="Configuration already exists"):
            await service.create_config(data)


class TestModelPrinterConfigServiceRead:
    """Tests for configuration retrieval."""

    @pytest.mark.asyncio
    async def test_get_config_by_id(self, db_session, test_tenant, test_model_printer_config):
        """Test retrieving a configuration by ID."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        config = await service.get_config(test_model_printer_config.id)

        assert config is not None
        assert config.id == test_model_printer_config.id

    @pytest.mark.asyncio
    async def test_get_config_not_found(self, db_session, test_tenant):
        """Test retrieving non-existent config returns None."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        config = await service.get_config(uuid4())

        assert config is None

    @pytest.mark.asyncio
    async def test_get_config_by_model_printer(
        self, db_session, test_tenant, test_model, test_printer, test_model_printer_config
    ):
        """Test retrieving config by model and printer IDs."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        config = await service.get_config_by_model_printer(
            test_model.id,
            test_printer.id,
        )

        assert config is not None
        assert config.id == test_model_printer_config.id

    @pytest.mark.asyncio
    async def test_get_config_by_model_printer_not_found(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test retrieving non-existent model-printer combo returns None."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        config = await service.get_config_by_model_printer(
            test_model.id,
            uuid4(),  # Non-existent printer
        )

        assert config is None

    @pytest.mark.asyncio
    async def test_get_config_tenant_isolation(
        self, db_session, test_tenant, test_model_printer_config
    ):
        """Test that config retrieval respects tenant isolation."""
        # Create another tenant
        from app.models.tenant import Tenant

        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant",
            slug="other-tenant",
        )
        db_session.add(other_tenant)
        await db_session.commit()

        other_service = ModelPrinterConfigService(db_session, other_tenant)

        # Other tenant shouldn't see the config
        config = await other_service.get_config(test_model_printer_config.id)

        assert config is None


class TestModelPrinterConfigServiceList:
    """Tests for listing configurations."""

    @pytest.mark.asyncio
    async def test_list_configs_for_model(
        self, db_session, test_tenant, test_model, test_printer, test_model_printer_config
    ):
        """Test listing configurations for a specific model."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        result = await service.list_configs_for_model(test_model.id)

        assert result.total == 1
        assert len(result.configs) == 1
        assert result.configs[0].model_id == test_model.id

    @pytest.mark.asyncio
    async def test_list_configs_for_model_empty(self, db_session, test_tenant, test_model):
        """Test listing configs for model with no configs returns empty."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        result = await service.list_configs_for_model(test_model.id)

        assert result.total == 0
        assert result.configs == []

    @pytest.mark.asyncio
    async def test_list_configs_for_printer(
        self, db_session, test_tenant, test_model, test_printer, test_model_printer_config
    ):
        """Test listing configurations for a specific printer."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        result = await service.list_configs_for_printer(test_printer.id)

        assert result.total == 1
        assert len(result.configs) == 1
        assert result.configs[0].printer_id == test_printer.id

    @pytest.mark.asyncio
    async def test_list_configs_for_printer_empty(self, db_session, test_tenant, test_printer):
        """Test listing configs for printer with no configs returns empty."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        result = await service.list_configs_for_printer(test_printer.id)

        assert result.total == 0
        assert result.configs == []

    @pytest.mark.asyncio
    async def test_list_configs_pagination(self, db_session, test_tenant, test_model):
        """Test listing configurations with pagination."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        # Create multiple printers and configs
        from app.models.printer import Printer

        for i in range(5):
            printer = Printer(
                id=uuid4(),
                tenant_id=test_tenant.id,
                name=f"Printer {i}",
            )
            db_session.add(printer)
            await db_session.flush()

            data = ModelPrinterConfigCreate(
                model_id=test_model.id,
                printer_id=printer.id,
            )
            await service.create_config(data)

        # Test pagination
        result = await service.list_configs_for_model(test_model.id, skip=0, limit=2)

        assert result.total == 5
        assert len(result.configs) == 2
        assert result.skip == 0
        assert result.limit == 2


class TestModelPrinterConfigServiceUpdate:
    """Tests for configuration updates."""

    @pytest.mark.asyncio
    async def test_update_config_single_field(
        self, db_session, test_tenant, test_model_printer_config
    ):
        """Test updating a single field."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        update = ModelPrinterConfigUpdate(prints_per_plate=6)
        updated = await service.update_config(test_model_printer_config.id, update)

        assert updated is not None
        assert updated.prints_per_plate == 6

    @pytest.mark.asyncio
    async def test_update_config_multiple_fields(
        self, db_session, test_tenant, test_model_printer_config
    ):
        """Test updating multiple fields."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        update = ModelPrinterConfigUpdate(
            prints_per_plate=8,
            print_time_minutes=90,
            material_weight_grams=Decimal("75.0"),
            supports=True,
        )
        updated = await service.update_config(test_model_printer_config.id, update)

        assert updated.prints_per_plate == 8
        assert updated.print_time_minutes == 90
        assert updated.material_weight_grams == Decimal("75.0")
        assert updated.supports is True

    @pytest.mark.asyncio
    async def test_update_config_not_found(self, db_session, test_tenant):
        """Test updating non-existent config returns None."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        update = ModelPrinterConfigUpdate(prints_per_plate=10)
        result = await service.update_config(uuid4(), update)

        assert result is None


class TestModelPrinterConfigServiceDelete:
    """Tests for configuration deletion."""

    @pytest.mark.asyncio
    async def test_delete_config(self, db_session, test_tenant, test_model_printer_config):
        """Test deleting a configuration."""
        service = ModelPrinterConfigService(db_session, test_tenant)
        config_id = test_model_printer_config.id

        result = await service.delete_config(config_id)

        assert result is True

        # Verify deletion
        config = await service.get_config(config_id)
        assert config is None

    @pytest.mark.asyncio
    async def test_delete_config_not_found(self, db_session, test_tenant):
        """Test deleting non-existent config returns False."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        result = await service.delete_config(uuid4())

        assert result is False


class TestModelPrinterConfigServiceGetOrCreate:
    """Tests for get_or_create functionality."""

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(
        self, db_session, test_tenant, test_model, test_printer, test_model_printer_config
    ):
        """Test get_or_create returns existing config."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        config, created = await service.get_or_create_config(
            test_model.id,
            test_printer.id,
        )

        assert config.id == test_model_printer_config.id
        assert created is False

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test get_or_create creates new config when none exists."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        config, created = await service.get_or_create_config(
            test_model.id,
            test_printer.id,
        )

        assert config is not None
        assert config.model_id == test_model.id
        assert config.printer_id == test_printer.id
        assert created is True

    @pytest.mark.asyncio
    async def test_get_or_create_with_defaults(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test get_or_create with custom defaults."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        defaults = ModelPrinterConfigCreate(
            model_id=uuid4(),  # Will be overwritten
            printer_id=uuid4(),  # Will be overwritten
            prints_per_plate=5,
            print_time_minutes=50,
            material_weight_grams=Decimal("40.0"),
        )

        config, created = await service.get_or_create_config(
            test_model.id,
            test_printer.id,
            defaults=defaults,
        )

        assert created is True
        assert config.model_id == test_model.id  # Overwritten
        assert config.printer_id == test_printer.id  # Overwritten
        assert config.prints_per_plate == 5
        assert config.print_time_minutes == 50
        assert config.material_weight_grams == Decimal("40.0")


class TestModelPrinterConfigServiceRelationships:
    """Tests for configuration relationship loading."""

    @pytest.mark.asyncio
    async def test_config_loads_model_relationship(
        self, db_session, test_tenant, test_model_printer_config
    ):
        """Test that config loads model relationship."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        config = await service.get_config(test_model_printer_config.id)

        assert config.model is not None
        assert config.model.id == test_model_printer_config.model_id

    @pytest.mark.asyncio
    async def test_config_loads_printer_relationship(
        self, db_session, test_tenant, test_model_printer_config
    ):
        """Test that config loads printer relationship."""
        service = ModelPrinterConfigService(db_session, test_tenant)

        config = await service.get_config(test_model_printer_config.id)

        assert config.printer is not None
        assert config.printer.id == test_model_printer_config.printer_id
