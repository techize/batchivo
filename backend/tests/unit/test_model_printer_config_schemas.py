"""Unit tests for ModelPrinterConfig Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.model_printer_config import (
    ModelPrinterConfigBase,
    ModelPrinterConfigCreate,
    ModelPrinterConfigUpdate,
    ModelPrinterConfigResponse,
    ModelPrinterConfigSummary,
    ModelPrinterConfigListResponse,
)
from app.schemas.printer import PrinterSummary
from app.schemas.production_run import ModelSummary


class TestModelPrinterConfigBase:
    """Tests for ModelPrinterConfigBase schema."""

    def test_config_base_valid_minimal(self):
        """Test creating config with only defaults."""
        config = ModelPrinterConfigBase()
        assert config.prints_per_plate == 1  # Default
        assert config.print_time_minutes is None
        assert config.material_weight_grams is None
        assert config.supports is False  # Default
        assert config.brim is False  # Default

    def test_config_base_valid_full(self):
        """Test creating config with all fields."""
        data = {
            "prints_per_plate": 3,
            "print_time_minutes": 45,
            "material_weight_grams": Decimal("30.5"),
            "bed_temperature": 60,
            "nozzle_temperature": 220,
            "layer_height": Decimal("0.20"),
            "infill_percentage": 15,
            "supports": True,
            "brim": True,
            "slicer_settings": {"speed": 80, "retraction": 2.0},
            "notes": "Optimal settings for this model",
        }
        config = ModelPrinterConfigBase(**data)
        assert config.prints_per_plate == 3
        assert config.print_time_minutes == 45
        assert config.material_weight_grams == Decimal("30.5")
        assert config.bed_temperature == 60
        assert config.nozzle_temperature == 220
        assert config.layer_height == Decimal("0.20")
        assert config.infill_percentage == 15
        assert config.supports is True
        assert config.brim is True
        assert config.slicer_settings == {"speed": 80, "retraction": 2.0}

    def test_config_base_prints_per_plate_zero_fails(self):
        """Test that prints_per_plate < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(prints_per_plate=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_config_base_negative_prints_per_plate_fails(self):
        """Test that negative prints_per_plate raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(prints_per_plate=-1)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_config_base_invalid_print_time_fails(self):
        """Test that print_time_minutes < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(print_time_minutes=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_config_base_invalid_material_weight_fails(self):
        """Test that material_weight_grams < 0.01 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(material_weight_grams=Decimal("0.001"))
        assert "greater than or equal to 0.01" in str(exc_info.value)

    def test_config_base_invalid_bed_temp_fails(self):
        """Test that bed_temperature > 200 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(bed_temperature=250)
        assert "less than or equal to 200" in str(exc_info.value)

    def test_config_base_invalid_nozzle_temp_fails(self):
        """Test that nozzle_temperature > 500 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(nozzle_temperature=600)
        assert "less than or equal to 500" in str(exc_info.value)

    def test_config_base_invalid_layer_height_fails(self):
        """Test that layer_height outside 0.04-1.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(layer_height=Decimal("0.01"))
        assert "greater than or equal to" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(layer_height=Decimal("1.5"))
        assert "less than or equal to" in str(exc_info.value)

    def test_config_base_invalid_infill_percentage_fails(self):
        """Test that infill_percentage outside 0-100 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(infill_percentage=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigBase(infill_percentage=101)
        assert "less than or equal to 100" in str(exc_info.value)


class TestModelPrinterConfigCreate:
    """Tests for ModelPrinterConfigCreate schema."""

    def test_config_create_valid(self):
        """Test creating a valid config."""
        model_id = uuid4()
        printer_id = uuid4()
        data = {
            "model_id": model_id,
            "printer_id": printer_id,
            "prints_per_plate": 4,
            "print_time_minutes": 60,
        }
        config = ModelPrinterConfigCreate(**data)
        assert config.model_id == model_id
        assert config.printer_id == printer_id
        assert config.prints_per_plate == 4

    def test_config_create_requires_model_id(self):
        """Test that model_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigCreate(printer_id=uuid4())
        assert "model_id" in str(exc_info.value)

    def test_config_create_requires_printer_id(self):
        """Test that printer_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigCreate(model_id=uuid4())
        assert "printer_id" in str(exc_info.value)


class TestModelPrinterConfigUpdate:
    """Tests for ModelPrinterConfigUpdate schema."""

    def test_config_update_all_optional(self):
        """Test that all fields are optional for update."""
        update = ModelPrinterConfigUpdate()
        assert update.prints_per_plate is None
        assert update.print_time_minutes is None
        assert update.supports is None

    def test_config_update_partial(self):
        """Test partial update with only some fields."""
        data = {
            "prints_per_plate": 6,
            "supports": True,
        }
        update = ModelPrinterConfigUpdate(**data)
        assert update.prints_per_plate == 6
        assert update.supports is True
        assert update.print_time_minutes is None

    def test_config_update_validation_still_applies(self):
        """Test that validation still applies for optional fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPrinterConfigUpdate(prints_per_plate=0)
        assert "greater than or equal to 1" in str(exc_info.value)


class TestModelPrinterConfigResponse:
    """Tests for ModelPrinterConfigResponse schema."""

    def test_config_response_valid(self):
        """Test creating a valid config response."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "prints_per_plate": 3,
            "print_time_minutes": 45,
            "material_weight_grams": Decimal("30.0"),
            "bed_temperature": 60,
            "nozzle_temperature": 220,
            "layer_height": None,
            "infill_percentage": None,
            "supports": False,
            "brim": False,
            "slicer_settings": {},
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }
        response = ModelPrinterConfigResponse(**data)
        assert response.prints_per_plate == 3
        assert response.print_time_minutes == 45

    def test_config_response_print_time_per_item_computed(self):
        """Test print_time_per_item_minutes computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "prints_per_plate": 3,
            "print_time_minutes": 90,  # 90 / 3 = 30 per item
            "supports": False,
            "brim": False,
            "created_at": now,
            "updated_at": now,
        }
        response = ModelPrinterConfigResponse(**data)
        assert response.print_time_per_item_minutes == 30

    def test_config_response_print_time_per_item_none_when_no_time(self):
        """Test print_time_per_item_minutes is None when print_time is None."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "prints_per_plate": 3,
            "print_time_minutes": None,
            "supports": False,
            "brim": False,
            "created_at": now,
            "updated_at": now,
        }
        response = ModelPrinterConfigResponse(**data)
        assert response.print_time_per_item_minutes is None

    def test_config_response_material_weight_per_plate_computed(self):
        """Test material_weight_per_plate_grams computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "prints_per_plate": 4,
            "material_weight_grams": Decimal("10.0"),  # 10 × 4 = 40
            "supports": False,
            "brim": False,
            "created_at": now,
            "updated_at": now,
        }
        response = ModelPrinterConfigResponse(**data)
        assert response.material_weight_per_plate_grams == 40.0

    def test_config_response_material_weight_per_plate_none_when_no_weight(self):
        """Test material_weight_per_plate is None when weight is None."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "prints_per_plate": 4,
            "material_weight_grams": None,
            "supports": False,
            "brim": False,
            "created_at": now,
            "updated_at": now,
        }
        response = ModelPrinterConfigResponse(**data)
        assert response.material_weight_per_plate_grams is None

    def test_config_response_with_nested_model_and_printer(self):
        """Test config response with nested model and printer summaries."""
        now = datetime.now()
        model_summary = ModelSummary(id=uuid4(), sku="DRG-001", name="Dragon Body")
        printer_summary = PrinterSummary(id=uuid4(), name="Bambu A1 Mini")

        data = {
            "id": uuid4(),
            "model_id": model_summary.id,
            "printer_id": printer_summary.id,
            "prints_per_plate": 3,
            "supports": False,
            "brim": False,
            "created_at": now,
            "updated_at": now,
            "model": model_summary,
            "printer": printer_summary,
        }
        response = ModelPrinterConfigResponse(**data)
        assert response.model.name == "Dragon Body"
        assert response.printer.name == "Bambu A1 Mini"

    def test_config_response_from_attributes(self):
        """Test that from_attributes is enabled for ORM conversion."""
        assert ModelPrinterConfigResponse.model_config.get("from_attributes") is True


class TestModelPrinterConfigSummary:
    """Tests for ModelPrinterConfigSummary schema."""

    def test_config_summary_valid(self):
        """Test creating a valid config summary."""
        data = {
            "id": uuid4(),
            "printer_id": uuid4(),
            "prints_per_plate": 3,
            "print_time_minutes": 45,
        }
        summary = ModelPrinterConfigSummary(**data)
        assert summary.prints_per_plate == 3
        assert summary.print_time_minutes == 45

    def test_config_summary_minimal(self):
        """Test config summary with minimal fields."""
        data = {
            "id": uuid4(),
            "printer_id": uuid4(),
            "prints_per_plate": 1,
        }
        summary = ModelPrinterConfigSummary(**data)
        assert summary.print_time_minutes is None


class TestModelPrinterConfigListResponse:
    """Tests for ModelPrinterConfigListResponse schema."""

    def test_config_list_response_valid(self):
        """Test creating a valid list response."""
        now = datetime.now()
        config_data = {
            "id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "prints_per_plate": 3,
            "supports": False,
            "brim": False,
            "created_at": now,
            "updated_at": now,
        }
        data = {
            "configs": [ModelPrinterConfigResponse(**config_data)],
            "total": 1,
            "skip": 0,
            "limit": 10,
        }
        response = ModelPrinterConfigListResponse(**data)
        assert len(response.configs) == 1
        assert response.total == 1

    def test_config_list_response_empty(self):
        """Test list response with empty list."""
        data = {
            "configs": [],
            "total": 0,
            "skip": 0,
            "limit": 10,
        }
        response = ModelPrinterConfigListResponse(**data)
        assert len(response.configs) == 0


class TestModelPrinterConfigEdgeCases:
    """Edge case tests for ModelPrinterConfig schemas."""

    def test_slicer_settings_complex_structure(self):
        """Test slicer_settings with complex nested structure."""
        settings = {
            "speed": {
                "print": 80,
                "travel": 150,
                "infill": 100,
            },
            "retraction": {
                "distance": 2.0,
                "speed": 40,
            },
            "cooling": {
                "fan_speed": [100, 80, 60],
                "min_layer_time": 10,
            },
        }
        config = ModelPrinterConfigBase(slicer_settings=settings)
        assert config.slicer_settings["speed"]["print"] == 80
        assert config.slicer_settings["cooling"]["fan_speed"] == [100, 80, 60]

    def test_layer_height_edge_values(self):
        """Test layer height at boundary values."""
        # Min value
        config1 = ModelPrinterConfigBase(layer_height=Decimal("0.04"))
        assert config1.layer_height == Decimal("0.04")

        # Max value
        config2 = ModelPrinterConfigBase(layer_height=Decimal("1.0"))
        assert config2.layer_height == Decimal("1.0")

    def test_infill_percentage_edge_values(self):
        """Test infill percentage at boundary values."""
        # 0% infill
        config1 = ModelPrinterConfigBase(infill_percentage=0)
        assert config1.infill_percentage == 0

        # 100% infill
        config2 = ModelPrinterConfigBase(infill_percentage=100)
        assert config2.infill_percentage == 100

    def test_decimal_material_weight_precision(self):
        """Test decimal precision for material weight."""
        config = ModelPrinterConfigBase(material_weight_grams=Decimal("30.125"))
        assert config.material_weight_grams == Decimal("30.125")

    def test_high_prints_per_plate(self):
        """Test high prints_per_plate value."""
        config = ModelPrinterConfigBase(prints_per_plate=100)
        assert config.prints_per_plate == 100
