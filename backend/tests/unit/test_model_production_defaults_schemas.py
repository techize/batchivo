"""Unit tests for Model Production Defaults Pydantic schemas."""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.model import (
    BOMSpoolSuggestion,
    ModelProductionDefaults,
)


class TestBOMSpoolSuggestion:
    """Tests for BOMSpoolSuggestion schema."""

    def test_bom_spool_suggestion_valid(self):
        """Test creating a valid BOM spool suggestion."""
        data = {
            "spool_id": uuid4(),
            "spool_name": "eSun - PLA - Red",
            "material_type_code": "PLA",
            "color": "Red",
            "color_hex": "#FF0000",
            "weight_grams": Decimal("50.5"),
            "cost_per_gram": Decimal("0.025"),
            "current_weight": Decimal("750.0"),
            "is_active": True,
        }
        suggestion = BOMSpoolSuggestion(**data)
        assert suggestion.spool_name == "eSun - PLA - Red"
        assert suggestion.material_type_code == "PLA"
        assert suggestion.weight_grams == Decimal("50.5")
        assert suggestion.is_active is True

    def test_bom_spool_suggestion_without_color_hex(self):
        """Test that color_hex is optional."""
        data = {
            "spool_id": uuid4(),
            "spool_name": "eSun - PLA - Red",
            "material_type_code": "PLA",
            "color": "Red",
            "color_hex": None,
            "weight_grams": Decimal("50.5"),
            "cost_per_gram": Decimal("0.025"),
            "current_weight": Decimal("750.0"),
            "is_active": True,
        }
        suggestion = BOMSpoolSuggestion(**data)
        assert suggestion.color_hex is None
        assert suggestion.color == "Red"

    def test_bom_spool_suggestion_inactive_spool(self):
        """Test BOM suggestion with inactive spool."""
        data = {
            "spool_id": uuid4(),
            "spool_name": "eSun - PLA - Red",
            "material_type_code": "PLA",
            "color": "Red",
            "color_hex": "#FF0000",
            "weight_grams": Decimal("50.5"),
            "cost_per_gram": Decimal("0.025"),
            "current_weight": Decimal("0.0"),  # Empty spool
            "is_active": False,  # Inactive
        }
        suggestion = BOMSpoolSuggestion(**data)
        assert suggestion.is_active is False
        assert suggestion.current_weight == Decimal("0.0")

    def test_bom_spool_suggestion_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        data = {
            "spool_id": uuid4(),
            "spool_name": "eSun - PLA - Red",
            # Missing material_type_code
            "color": "Red",
            "weight_grams": Decimal("50.5"),
            "cost_per_gram": Decimal("0.025"),
            "current_weight": Decimal("750.0"),
            "is_active": True,
        }
        with pytest.raises(ValidationError) as exc_info:
            BOMSpoolSuggestion(**data)
        assert "material_type_code" in str(exc_info.value)


class TestModelProductionDefaults:
    """Tests for ModelProductionDefaults schema."""

    def test_model_production_defaults_valid(self):
        """Test creating valid model production defaults."""
        bom_material = BOMSpoolSuggestion(
            spool_id=uuid4(),
            spool_name="eSun - PLA - Blue",
            material_type_code="PLA",
            color="Blue",
            color_hex="#0000FF",
            weight_grams=Decimal("100.0"),
            cost_per_gram=Decimal("0.025"),
            current_weight=Decimal("800.0"),
            is_active=True,
        )

        data = {
            "model_id": uuid4(),
            "sku": "MODEL-001",
            "name": "Test Model",
            "machine": "Prusa i3 MK3S",
            "print_time_minutes": 300,
            "prints_per_plate": 5,
            "bom_materials": [bom_material],
        }
        defaults = ModelProductionDefaults(**data)
        assert defaults.sku == "MODEL-001"
        assert defaults.name == "Test Model"
        assert defaults.machine == "Prusa i3 MK3S"
        assert defaults.print_time_minutes == 300
        assert defaults.prints_per_plate == 5
        assert len(defaults.bom_materials) == 1
        assert defaults.bom_materials[0].material_type_code == "PLA"

    def test_model_production_defaults_no_machine(self):
        """Test that machine is optional."""
        data = {
            "model_id": uuid4(),
            "sku": "MODEL-002",
            "name": "Test Model 2",
            "machine": None,
            "print_time_minutes": 180,
            "prints_per_plate": 1,
            "bom_materials": [],
        }
        defaults = ModelProductionDefaults(**data)
        assert defaults.machine is None
        assert defaults.print_time_minutes == 180

    def test_model_production_defaults_no_print_time(self):
        """Test that print_time_minutes is optional."""
        data = {
            "model_id": uuid4(),
            "sku": "MODEL-003",
            "name": "Test Model 3",
            "machine": "Prusa Mini",
            "print_time_minutes": None,
            "prints_per_plate": 2,
            "bom_materials": [],
        }
        defaults = ModelProductionDefaults(**data)
        assert defaults.print_time_minutes is None
        assert defaults.prints_per_plate == 2

    def test_model_production_defaults_empty_bom(self):
        """Test model with no BOM materials."""
        data = {
            "model_id": uuid4(),
            "sku": "MODEL-004",
            "name": "Test Model 4",
            "machine": "Ender 3",
            "print_time_minutes": 120,
            "prints_per_plate": 1,
            "bom_materials": [],
        }
        defaults = ModelProductionDefaults(**data)
        assert len(defaults.bom_materials) == 0

    def test_model_production_defaults_multi_material_bom(self):
        """Test model with multiple BOM materials."""
        bom_materials = [
            BOMSpoolSuggestion(
                spool_id=uuid4(),
                spool_name="eSun - PLA - Blue",
                material_type_code="PLA",
                color="Blue",
                color_hex="#0000FF",
                weight_grams=Decimal("50.0"),
                cost_per_gram=Decimal("0.025"),
                current_weight=Decimal("800.0"),
                is_active=True,
            ),
            BOMSpoolSuggestion(
                spool_id=uuid4(),
                spool_name="eSun - PLA - Red",
                material_type_code="PLA",
                color="Red",
                color_hex="#FF0000",
                weight_grams=Decimal("30.0"),
                cost_per_gram=Decimal("0.025"),
                current_weight=Decimal("600.0"),
                is_active=True,
            ),
            BOMSpoolSuggestion(
                spool_id=uuid4(),
                spool_name="Prusament - PETG - Black",
                material_type_code="PETG",
                color="Black",
                color_hex="#000000",
                weight_grams=Decimal("20.0"),
                cost_per_gram=Decimal("0.030"),
                current_weight=Decimal("500.0"),
                is_active=True,
            ),
        ]

        data = {
            "model_id": uuid4(),
            "sku": "MODEL-005",
            "name": "Multi-Color Model",
            "machine": "Prusa XL",
            "print_time_minutes": 600,
            "prints_per_plate": 3,
            "bom_materials": bom_materials,
        }
        defaults = ModelProductionDefaults(**data)
        assert len(defaults.bom_materials) == 3
        assert defaults.bom_materials[0].color == "Blue"
        assert defaults.bom_materials[1].color == "Red"
        assert defaults.bom_materials[2].material_type_code == "PETG"
        assert defaults.prints_per_plate == 3

    def test_model_production_defaults_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        data = {
            "model_id": uuid4(),
            # Missing sku
            "name": "Test Model",
            "machine": "Prusa i3 MK3S",
            "print_time_minutes": 300,
            "prints_per_plate": 5,
            "bom_materials": [],
        }
        with pytest.raises(ValidationError) as exc_info:
            ModelProductionDefaults(**data)
        assert "sku" in str(exc_info.value)

    def test_model_production_defaults_batch_printing(self):
        """Test model with batch printing (prints_per_plate > 1)."""
        data = {
            "model_id": uuid4(),
            "sku": "BATCH-001",
            "name": "Batch Print Model",
            "machine": "Prusa XL",
            "print_time_minutes": 480,  # 8 hours for full plate
            "prints_per_plate": 10,  # 10 items per plate
            "bom_materials": [],
        }
        defaults = ModelProductionDefaults(**data)
        assert defaults.prints_per_plate == 10
        # Verify time per item would be: 480 / 10 = 48 minutes
        time_per_item = defaults.print_time_minutes / defaults.prints_per_plate
        assert time_per_item == 48.0
