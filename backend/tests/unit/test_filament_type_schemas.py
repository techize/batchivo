"""Tests for FilamentType Pydantic schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.filament_type import FilamentTypeBase, FilamentTypeCreate, FilamentTypeUpdate


def valid_filament_type(**kwargs) -> dict:
    defaults = {
        "material_type_id": uuid4(),
        "brand": "Bambu Lab",
        "color": "Black",
        "diameter": 1.75,
    }
    defaults.update(kwargs)
    return defaults


class TestFilamentTypeBase:
    def test_valid_minimal(self):
        ft = FilamentTypeCreate(**valid_filament_type())
        assert ft.brand == "Bambu Lab"
        assert ft.color == "Black"
        assert ft.diameter == 1.75
        assert ft.has_sample is False  # DATA-04

    # --- brand ---
    def test_brand_empty_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(brand=""))

    def test_brand_max_100_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(brand="B" * 100))
        assert len(ft.brand) == 100

    def test_brand_over_100_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(brand="B" * 101))

    # --- color ---
    def test_color_empty_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(color=""))

    def test_color_max_50_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(color="C" * 50))
        assert len(ft.color) == 50

    def test_color_over_50_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(color="C" * 51))

    # --- diameter ---
    def test_diameter_zero_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(diameter=0))

    def test_diameter_negative_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(diameter=-1.0))

    def test_diameter_above_max_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(diameter=5.1))

    def test_diameter_exactly_5_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(diameter=5.0))
        assert ft.diameter == 5.0

    def test_diameter_defaults_175(self):
        data = valid_filament_type()
        del data["diameter"]
        ft = FilamentTypeBase(**data)
        assert ft.diameter == 1.75

    # --- extruder_temp ---
    def test_extruder_temp_below_min_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(extruder_temp=149))

    def test_extruder_temp_min_150_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(extruder_temp=150))
        assert ft.extruder_temp == 150

    def test_extruder_temp_max_400_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(extruder_temp=400))
        assert ft.extruder_temp == 400

    def test_extruder_temp_above_max_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(extruder_temp=401))

    def test_extruder_temp_none_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(extruder_temp=None))
        assert ft.extruder_temp is None

    # --- bed_temp ---
    def test_bed_temp_negative_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(bed_temp=-1))

    def test_bed_temp_zero_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(bed_temp=0))
        assert ft.bed_temp == 0

    def test_bed_temp_max_150_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(bed_temp=150))
        assert ft.bed_temp == 150

    def test_bed_temp_above_max_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(bed_temp=151))

    def test_bed_temp_none_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(bed_temp=None))
        assert ft.bed_temp is None

    # --- has_sample (DATA-04) ---
    def test_has_sample_defaults_false(self):
        """DATA-04: has_sample defaults to False."""
        ft = FilamentTypeBase(**valid_filament_type())
        assert ft.has_sample is False

    def test_has_sample_can_be_set_true(self):
        ft = FilamentTypeBase(**valid_filament_type(has_sample=True))
        assert ft.has_sample is True

    # --- density ---
    def test_density_zero_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(density=0))

    def test_density_above_max_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeBase(**valid_filament_type(density=10.1))

    def test_density_max_10_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(density=10.0))
        assert ft.density == 10.0

    def test_density_none_accepted(self):
        ft = FilamentTypeBase(**valid_filament_type(density=None))
        assert ft.density is None

    # --- optional boolean defaults ---
    def test_translucent_defaults_false(self):
        ft = FilamentTypeBase(**valid_filament_type())
        assert ft.translucent is False

    def test_glow_defaults_false(self):
        ft = FilamentTypeBase(**valid_filament_type())
        assert ft.glow is False


class TestFilamentTypeCreate:
    def test_inherits_from_base(self):
        ft = FilamentTypeCreate(**valid_filament_type())
        assert ft.brand == "Bambu Lab"
        assert ft.color == "Black"

    def test_material_type_id_required(self):
        data = valid_filament_type()
        del data["material_type_id"]
        with pytest.raises(ValidationError):
            FilamentTypeCreate(**data)


class TestFilamentTypeUpdate:
    def test_all_optional(self):
        """FilamentTypeUpdate must accept no arguments (all fields optional)."""
        u = FilamentTypeUpdate()
        assert u.brand is None
        assert u.color is None
        assert u.diameter is None
        assert u.has_sample is None

    def test_partial_update_brand_only(self):
        u = FilamentTypeUpdate(brand="Polymaker")
        assert u.brand == "Polymaker"
        assert u.color is None

    def test_partial_update_multiple_fields(self):
        u = FilamentTypeUpdate(brand="Bambu Lab", color="White", extruder_temp=220)
        assert u.brand == "Bambu Lab"
        assert u.color == "White"
        assert u.extruder_temp == 220

    def test_update_brand_empty_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeUpdate(brand="")

    def test_update_color_empty_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeUpdate(color="")

    def test_update_diameter_above_max_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeUpdate(diameter=5.1)

    def test_update_extruder_temp_below_min_raises(self):
        with pytest.raises(ValidationError):
            FilamentTypeUpdate(extruder_temp=149)
