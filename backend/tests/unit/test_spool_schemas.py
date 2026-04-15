"""
Tests for Spool Pydantic schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.spool import SpoolBase, SpoolCreate, SpoolUpdate


def valid_spool(**kwargs) -> dict:
    defaults = {
        "spool_id": "SPOOL-001",
        "material_type_id": uuid4(),
        "brand": "Bambu Lab",
        "color": "Jade White",
        "initial_weight": 1000.0,
        "current_weight": 750.0,
    }
    defaults.update(kwargs)
    return defaults


class TestSpoolBase:
    def test_valid_minimal(self):
        s = SpoolBase(**valid_spool())
        assert s.brand == "Bambu Lab"
        assert s.diameter == 1.75  # default
        assert s.translucent is False
        assert s.glow is False
        assert s.is_active is True

    def test_spool_id_empty_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(spool_id=""))

    def test_spool_id_too_long_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(spool_id="S" * 51))

    def test_brand_empty_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(brand=""))

    def test_color_empty_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(color=""))

    # --- Diameter ---
    def test_diameter_zero_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(diameter=0))

    def test_diameter_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(diameter=-1.0))

    def test_diameter_above_max_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(diameter=5.1))

    def test_diameter_exactly_5_accepted(self):
        s = SpoolBase(**valid_spool(diameter=5.0))
        assert s.diameter == 5.0

    # --- Extruder temp ---
    def test_extruder_temp_below_min_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(extruder_temp=149))

    def test_extruder_temp_min_150(self):
        s = SpoolBase(**valid_spool(extruder_temp=150))
        assert s.extruder_temp == 150

    def test_extruder_temp_max_400(self):
        s = SpoolBase(**valid_spool(extruder_temp=400))
        assert s.extruder_temp == 400

    def test_extruder_temp_above_max_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(extruder_temp=401))

    # --- Bed temp ---
    def test_bed_temp_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(bed_temp=-1))

    def test_bed_temp_zero_accepted(self):
        s = SpoolBase(**valid_spool(bed_temp=0))
        assert s.bed_temp == 0

    def test_bed_temp_max_150(self):
        s = SpoolBase(**valid_spool(bed_temp=150))
        assert s.bed_temp == 150

    def test_bed_temp_above_max_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(bed_temp=151))

    # --- Weight ---
    def test_initial_weight_zero_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(initial_weight=0))

    def test_initial_weight_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(initial_weight=-100))

    def test_current_weight_zero_accepted(self):
        s = SpoolBase(**valid_spool(current_weight=0))
        assert s.current_weight == 0

    def test_current_weight_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(current_weight=-1))

    def test_purchase_price_zero_accepted(self):
        s = SpoolBase(**valid_spool(purchase_price=0))
        assert s.purchase_price == 0

    def test_purchase_price_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(purchase_price=-1.0))

    # --- Batch tracking ---
    def test_purchased_quantity_zero_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(purchased_quantity=0))

    def test_purchased_quantity_positive(self):
        s = SpoolBase(**valid_spool(purchased_quantity=5))
        assert s.purchased_quantity == 5

    def test_spools_remaining_zero_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(spools_remaining=0))

    # --- Density ---
    def test_density_zero_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(density=0))

    def test_density_above_max_raises(self):
        with pytest.raises(ValidationError):
            SpoolBase(**valid_spool(density=10.1))

    def test_density_valid(self):
        s = SpoolBase(**valid_spool(density=1.24))
        assert s.density == 1.24


class TestSpoolCreate:
    def test_inherits_from_base(self):
        s = SpoolCreate(**valid_spool())
        assert s.spool_id == "SPOOL-001"


class TestSpoolUpdate:
    def test_all_optional(self):
        u = SpoolUpdate()
        assert u.brand is None
        assert u.current_weight is None
        assert u.is_active is None

    def test_partial_update(self):
        u = SpoolUpdate(current_weight=500.0, is_active=False)
        assert u.current_weight == 500.0
        assert u.is_active is False

    def test_current_weight_negative_raises(self):
        with pytest.raises(ValidationError):
            SpoolUpdate(current_weight=-1.0)

    def test_extruder_temp_below_min_raises(self):
        with pytest.raises(ValidationError):
            SpoolUpdate(extruder_temp=100)

    def test_diameter_above_max_raises(self):
        with pytest.raises(ValidationError):
            SpoolUpdate(diameter=6.0)

    def test_spool_id_empty_raises(self):
        with pytest.raises(ValidationError):
            SpoolUpdate(spool_id="")
