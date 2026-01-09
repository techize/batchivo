"""Unit tests for ModelPrinterConfig model."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.model_printer_config import ModelPrinterConfig
from app.models.printer import Printer
from app.models.model import Model


class TestModelPrinterConfigModel:
    """Tests for ModelPrinterConfig model creation and properties."""

    @pytest.mark.asyncio
    async def test_create_config_basic(self, db_session, test_model, test_printer):
        """Test creating a basic config with required fields only."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.id is not None
        assert config.model_id == test_model.id
        assert config.printer_id == test_printer.id
        assert config.prints_per_plate == 3
        assert config.created_at is not None
        assert config.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_config_all_fields(self, db_session, test_model, test_printer):
        """Test creating a config with all fields populated."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=4,
            print_time_minutes=45,
            material_weight_grams=Decimal("30.5"),
            bed_temperature=65,
            nozzle_temperature=215,
            layer_height=Decimal("0.16"),
            infill_percentage=20,
            supports=True,
            brim=True,
            slicer_settings={
                "speed_infill": 200,
                "speed_wall": 150,
                "retraction_length": 0.8,
            },
            notes="Optimized settings for dragon bodies",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.prints_per_plate == 4
        assert config.print_time_minutes == 45
        assert config.material_weight_grams == Decimal("30.5")
        assert config.bed_temperature == 65
        assert config.nozzle_temperature == 215
        assert config.layer_height == Decimal("0.16")
        assert config.infill_percentage == 20
        assert config.supports is True
        assert config.brim is True
        assert config.slicer_settings["speed_infill"] == 200
        assert config.notes == "Optimized settings for dragon bodies"

    @pytest.mark.asyncio
    async def test_config_default_values(self, db_session, test_model, test_printer):
        """Test that default values are set correctly."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.prints_per_plate == 1  # Default
        assert config.supports is False
        assert config.brim is False


class TestModelPrinterConfigComputedProperties:
    """Tests for ModelPrinterConfig computed properties."""

    @pytest.mark.asyncio
    async def test_print_time_per_item_minutes(self, db_session, test_model, test_printer):
        """Test the print_time_per_item_minutes computed property."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
            print_time_minutes=90,  # 90 minutes for full plate
        )

        # 90 min / 3 items = 30 min per item
        assert config.print_time_per_item_minutes == 30

    @pytest.mark.asyncio
    async def test_print_time_per_item_minutes_none(self, db_session, test_model, test_printer):
        """Test print_time_per_item_minutes when print_time is None."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
            print_time_minutes=None,
        )

        assert config.print_time_per_item_minutes is None

    @pytest.mark.asyncio
    async def test_material_weight_per_plate_grams(self, db_session, test_model, test_printer):
        """Test the material_weight_per_plate_grams computed property."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=4,
            material_weight_grams=Decimal("25.0"),  # 25g per item
        )

        # 25g × 4 items = 100g per plate
        assert config.material_weight_per_plate_grams == Decimal("100.0")

    @pytest.mark.asyncio
    async def test_material_weight_per_plate_grams_none(self, db_session, test_model, test_printer):
        """Test material_weight_per_plate_grams when material_weight is None."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=4,
            material_weight_grams=None,
        )

        assert config.material_weight_per_plate_grams is None

    @pytest.mark.asyncio
    async def test_repr(self, db_session, test_model, test_printer):
        """Test the __repr__ method."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
        )

        repr_str = repr(config)
        assert "model_id=" in repr_str
        assert "printer_id=" in repr_str
        assert "prints_per_plate=3" in repr_str


class TestModelPrinterConfigConstraints:
    """Tests for ModelPrinterConfig model constraints."""

    @pytest.mark.asyncio
    async def test_unique_model_printer_pair(self, db_session, test_model, test_printer):
        """Test that model+printer combination must be unique."""
        config1 = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
        )
        db_session.add(config1)
        await db_session.commit()

        # Try to create another config for same model+printer
        config2 = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=4,
        )
        db_session.add(config2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_same_model_different_printers(
        self, db_session, test_model, test_printer, test_tenant
    ):
        """Test that same model can have configs for different printers."""
        # Create second printer
        printer2 = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Second Test Printer",
        )
        db_session.add(printer2)
        await db_session.commit()

        # Create config for first printer
        config1 = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
        )
        db_session.add(config1)
        await db_session.commit()

        # Create config for second printer - should succeed
        config2 = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=printer2.id,
            prints_per_plate=4,
        )
        db_session.add(config2)
        await db_session.commit()

        assert config1.printer_id != config2.printer_id
        assert config1.model_id == config2.model_id

    @pytest.mark.asyncio
    async def test_prints_per_plate_positive_constraint(self, db_session, test_model, test_printer):
        """Test that prints_per_plate must be positive."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=0,  # Invalid
        )
        db_session.add(config)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_cascade_delete_on_model(self, db_session, test_tenant, test_printer):
        """Test that config is deleted when model is deleted."""
        # Create model
        model = Model(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="DELETABLE-MODEL",
            name="Deletable Model",
        )
        db_session.add(model)
        await db_session.commit()

        # Create config
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=model.id,
            printer_id=test_printer.id,
            prints_per_plate=2,
        )
        db_session.add(config)
        await db_session.commit()

        config_id = config.id

        # Delete model
        await db_session.delete(model)
        await db_session.commit()

        # Verify config is deleted
        result = await db_session.execute(
            select(ModelPrinterConfig).where(ModelPrinterConfig.id == config_id)
        )
        deleted_config = result.scalar_one_or_none()
        assert deleted_config is None

    @pytest.mark.asyncio
    async def test_cascade_delete_on_printer(self, db_session, test_tenant, test_model):
        """Test that config is deleted when printer is deleted."""
        # Create printer
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Deletable Printer",
        )
        db_session.add(printer)
        await db_session.commit()

        # Create config
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=printer.id,
            prints_per_plate=2,
        )
        db_session.add(config)
        await db_session.commit()

        config_id = config.id

        # Delete printer
        await db_session.delete(printer)
        await db_session.commit()

        # Verify config is deleted
        result = await db_session.execute(
            select(ModelPrinterConfig).where(ModelPrinterConfig.id == config_id)
        )
        deleted_config = result.scalar_one_or_none()
        assert deleted_config is None


class TestModelPrinterConfigRelationships:
    """Tests for ModelPrinterConfig relationships."""

    @pytest.mark.asyncio
    async def test_config_model_relationship(self, db_session, test_model, test_printer):
        """Test the model relationship."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Access model through relationship
        assert config.model is not None
        assert config.model.id == test_model.id
        assert config.model.sku == test_model.sku

    @pytest.mark.asyncio
    async def test_config_printer_relationship(self, db_session, test_model, test_printer):
        """Test the printer relationship."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Access printer through relationship
        assert config.printer is not None
        assert config.printer.id == test_printer.id
        assert config.printer.name == test_printer.name

    @pytest.mark.asyncio
    async def test_model_printer_configs_relationship(
        self, db_session, test_model, test_printer, test_tenant
    ):
        """Test accessing configs from model."""
        # Create second printer
        printer2 = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Second Printer",
        )
        db_session.add(printer2)
        await db_session.commit()

        # Create configs for both printers
        config1 = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
        )
        config2 = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=printer2.id,
            prints_per_plate=4,
        )
        db_session.add_all([config1, config2])
        await db_session.commit()
        await db_session.refresh(test_model)

        # Access configs through model relationship
        assert len(test_model.printer_configs) == 2


class TestModelPrinterConfigSlicerSettings:
    """Tests for slicer_settings JSONB field."""

    @pytest.mark.asyncio
    async def test_slicer_settings_storage(self, db_session, test_model, test_printer):
        """Test storing complex slicer settings in JSONB field."""
        slicer_settings = {
            "speed": {
                "infill": 200,
                "wall": 150,
                "travel": 300,
            },
            "retraction": {
                "length": 0.8,
                "speed": 30,
            },
            "quality": {
                "seam_position": "aligned",
                "ironing": True,
            },
            "profiles_used": ["0.20mm SPEED", "Bambu PLA Basic"],
        }

        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
            slicer_settings=slicer_settings,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Verify JSONB stored and retrieved correctly
        assert config.slicer_settings["speed"]["infill"] == 200
        assert config.slicer_settings["retraction"]["length"] == 0.8
        assert config.slicer_settings["quality"]["ironing"] is True
        assert "0.20mm SPEED" in config.slicer_settings["profiles_used"]

    @pytest.mark.asyncio
    async def test_slicer_settings_update(self, db_session, test_model, test_printer):
        """Test updating slicer settings."""
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=test_printer.id,
            prints_per_plate=3,
            slicer_settings={"speed_infill": 150},
        )
        db_session.add(config)
        await db_session.commit()

        # Update settings
        config.slicer_settings = {"speed_infill": 200, "new_setting": True}
        await db_session.commit()
        await db_session.refresh(config)

        assert config.slicer_settings["speed_infill"] == 200
        assert config.slicer_settings["new_setting"] is True
