"""
Tests for MaterialType Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.material import MaterialTypeBase, MaterialTypeCreate, MaterialTypeUpdate


class TestMaterialTypeBase:
    def _valid(self, **kwargs) -> dict:
        defaults = {"code": "PLA", "name": "Polylactic Acid"}
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        m = MaterialTypeBase(**self._valid())
        assert m.code == "PLA"
        assert m.is_active is True

    def test_code_too_long_raises(self):
        with pytest.raises(ValidationError):
            MaterialTypeBase(**self._valid(code="C" * 21))

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            MaterialTypeBase(**self._valid(name="N" * 101))

    def test_typical_density_negative_raises(self):
        with pytest.raises(ValidationError):
            MaterialTypeBase(**self._valid(typical_density=-0.1))

    def test_typical_density_zero_accepted(self):
        m = MaterialTypeBase(**self._valid(typical_density=0.0))
        assert m.typical_density == 0.0

    def test_typical_cost_per_kg_negative_raises(self):
        with pytest.raises(ValidationError):
            MaterialTypeBase(**self._valid(typical_cost_per_kg=-1.0))

    def test_min_temp_negative_raises(self):
        with pytest.raises(ValidationError):
            MaterialTypeBase(**self._valid(min_temp=-1))

    def test_min_temp_zero_accepted(self):
        m = MaterialTypeBase(**self._valid(min_temp=0))
        assert m.min_temp == 0

    def test_min_temp_max_500(self):
        m = MaterialTypeBase(**self._valid(min_temp=500))
        assert m.min_temp == 500

    def test_min_temp_above_max_raises(self):
        with pytest.raises(ValidationError):
            MaterialTypeBase(**self._valid(min_temp=501))

    def test_max_temp_above_max_raises(self):
        with pytest.raises(ValidationError):
            MaterialTypeBase(**self._valid(max_temp=501))

    def test_bed_temp_max_200(self):
        m = MaterialTypeBase(**self._valid(bed_temp=200))
        assert m.bed_temp == 200

    def test_bed_temp_above_max_raises(self):
        with pytest.raises(ValidationError):
            MaterialTypeBase(**self._valid(bed_temp=201))

    def test_all_optional_fields_none_by_default(self):
        m = MaterialTypeBase(**self._valid())
        assert m.description is None
        assert m.typical_density is None
        assert m.min_temp is None
        assert m.max_temp is None
        assert m.bed_temp is None


class TestMaterialTypeCreate:
    def test_inherits_from_base(self):
        m = MaterialTypeCreate(code="PETG", name="Polyethylene Terephthalate Glycol")
        assert m.code == "PETG"


class TestMaterialTypeUpdate:
    def test_all_optional(self):
        u = MaterialTypeUpdate()
        assert u.name is None
        assert u.is_active is None

    def test_partial_update(self):
        u = MaterialTypeUpdate(is_active=False, min_temp=180)
        assert u.is_active is False
        assert u.min_temp == 180
