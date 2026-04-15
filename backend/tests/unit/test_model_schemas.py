"""
Tests for Model (3D print model) Pydantic schemas.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.model import (
    BOMSpoolSuggestion,
    CostBreakdown,
    ModelBase,
    ModelComponentBase,
    ModelCreate,
    ModelListResponse,
    ModelMaterialBase,
    ModelProductionDefaults,
    ModelUpdate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestCostBreakdown:
    def test_valid(self):
        c = CostBreakdown(
            material_cost=Decimal("2.50"),
            component_cost=Decimal("0.30"),
            labor_cost=Decimal("5.00"),
            overhead_cost=Decimal("0.75"),
            total_cost=Decimal("8.55"),
        )
        assert c.total_cost == Decimal("8.55")


class TestModelMaterialBase:
    def test_valid(self):
        m = ModelMaterialBase(
            spool_id=uuid4(),
            weight_grams=Decimal("10.5"),
            cost_per_gram=Decimal("0.025"),
        )
        assert m.weight_grams == Decimal("10.5")

    def test_weight_grams_zero_raises(self):
        with pytest.raises(ValidationError):
            ModelMaterialBase(
                spool_id=uuid4(),
                weight_grams=Decimal("0"),
                cost_per_gram=Decimal("0.02"),
            )

    def test_cost_per_gram_zero_accepted(self):
        m = ModelMaterialBase(
            spool_id=uuid4(),
            weight_grams=Decimal("5"),
            cost_per_gram=Decimal("0"),
        )
        assert m.cost_per_gram == Decimal("0")

    def test_cost_per_gram_negative_raises(self):
        with pytest.raises(ValidationError):
            ModelMaterialBase(
                spool_id=uuid4(),
                weight_grams=Decimal("5"),
                cost_per_gram=Decimal("-0.01"),
            )


class TestModelComponentBase:
    def test_valid(self):
        c = ModelComponentBase(
            component_name="Magnets N52",
            quantity=4,
            unit_cost=Decimal("0.10"),
        )
        assert c.component_name == "Magnets N52"
        assert c.supplier is None

    def test_component_name_empty_raises(self):
        with pytest.raises(ValidationError):
            ModelComponentBase(component_name="", quantity=1, unit_cost=Decimal("0"))

    def test_component_name_max_200(self):
        c = ModelComponentBase(component_name="C" * 200, quantity=1, unit_cost=Decimal("0"))
        assert len(c.component_name) == 200

    def test_component_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelComponentBase(component_name="C" * 201, quantity=1, unit_cost=Decimal("0"))

    def test_quantity_zero_raises(self):
        with pytest.raises(ValidationError):
            ModelComponentBase(component_name="Part", quantity=0, unit_cost=Decimal("0"))

    def test_unit_cost_zero_accepted(self):
        c = ModelComponentBase(component_name="Free Part", quantity=1, unit_cost=Decimal("0"))
        assert c.unit_cost == Decimal("0")

    def test_unit_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            ModelComponentBase(component_name="Part", quantity=1, unit_cost=Decimal("-0.01"))

    def test_supplier_max_200(self):
        c = ModelComponentBase(
            component_name="Part", quantity=1, unit_cost=Decimal("1"), supplier="S" * 200
        )
        assert len(c.supplier) == 200

    def test_supplier_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelComponentBase(
                component_name="Part", quantity=1, unit_cost=Decimal("1"), supplier="S" * 201
            )


class TestModelBase:
    def _valid(self, **kwargs) -> dict:
        defaults = {"sku": "MDL-001", "name": "Dragon V2"}
        defaults.update(kwargs)
        return defaults

    def test_defaults(self):
        m = ModelBase(**self._valid())
        assert m.is_active is True
        assert m.labor_hours == Decimal("0")
        assert m.overhead_percentage == Decimal("0")
        assert m.prints_per_plate == 1

    def test_sku_empty_raises(self):
        with pytest.raises(ValidationError):
            ModelBase(sku="", name="Dragon")

    def test_sku_max_100(self):
        m = ModelBase(sku="S" * 100, name="Test")
        assert len(m.sku) == 100

    def test_sku_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelBase(sku="S" * 101, name="Test")

    def test_name_max_200(self):
        m = ModelBase(sku="MDL", name="N" * 200)
        assert len(m.name) == 200

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelBase(sku="MDL", name="N" * 201)

    def test_labor_hours_negative_raises(self):
        with pytest.raises(ValidationError):
            ModelBase(**self._valid(labor_hours=Decimal("-0.1")))

    def test_overhead_percentage_max_100(self):
        m = ModelBase(**self._valid(overhead_percentage=Decimal("100")))
        assert m.overhead_percentage == Decimal("100")

    def test_overhead_percentage_above_100_raises(self):
        with pytest.raises(ValidationError):
            ModelBase(**self._valid(overhead_percentage=Decimal("100.01")))

    def test_prints_per_plate_minimum_1(self):
        with pytest.raises(ValidationError):
            ModelBase(**self._valid(prints_per_plate=0))

    def test_print_time_minutes_zero_accepted(self):
        m = ModelBase(**self._valid(print_time_minutes=0))
        assert m.print_time_minutes == 0

    def test_print_time_minutes_negative_raises(self):
        with pytest.raises(ValidationError):
            ModelBase(**self._valid(print_time_minutes=-1))

    def test_units_in_stock_zero_accepted(self):
        m = ModelBase(**self._valid(units_in_stock=0))
        assert m.units_in_stock == 0

    def test_units_in_stock_negative_raises(self):
        with pytest.raises(ValidationError):
            ModelBase(**self._valid(units_in_stock=-1))

    def test_image_url_max_500(self):
        m = ModelBase(**self._valid(image_url="https://x.com/" + "a" * 480))
        assert m.image_url is not None

    def test_image_url_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelBase(**self._valid(image_url="u" * 501))


class TestModelCreate:
    def test_inherits_base_defaults(self):
        m = ModelCreate(sku="MDL-002", name="Fire Drake")
        assert m.is_active is True
        assert m.prints_per_plate == 1


class TestModelUpdate:
    def test_all_optional(self):
        u = ModelUpdate()
        assert u.sku is None
        assert u.name is None
        assert u.is_active is None

    def test_partial_update(self):
        u = ModelUpdate(name="Updated Dragon", is_active=False)
        assert u.name == "Updated Dragon"
        assert u.is_active is False

    def test_sku_empty_raises(self):
        with pytest.raises(ValidationError):
            ModelUpdate(sku="")

    def test_overhead_above_100_raises(self):
        with pytest.raises(ValidationError):
            ModelUpdate(overhead_percentage=Decimal("101"))

    def test_prints_per_plate_zero_raises(self):
        with pytest.raises(ValidationError):
            ModelUpdate(prints_per_plate=0)


class TestBOMSpoolSuggestion:
    def test_valid(self):
        s = BOMSpoolSuggestion(
            spool_id=uuid4(),
            spool_name="Bambu PLA White",
            material_type_code="PLA",
            color="White",
            weight_grams=Decimal("15.0"),
            cost_per_gram=Decimal("0.025"),
            current_weight=Decimal("800.0"),
            is_active=True,
        )
        assert s.material_type_code == "PLA"
        assert s.color_hex is None

    def test_with_color_hex(self):
        s = BOMSpoolSuggestion(
            spool_id=uuid4(),
            spool_name="Bambu PLA Red",
            material_type_code="PLA",
            color="Red",
            color_hex="FF0000",
            weight_grams=Decimal("10"),
            cost_per_gram=Decimal("0.02"),
            current_weight=Decimal("500"),
            is_active=True,
        )
        assert s.color_hex == "FF0000"


class TestModelProductionDefaults:
    def test_valid_minimal(self):
        d = ModelProductionDefaults(
            model_id=uuid4(),
            sku="MDL-001",
            name="Dragon V2",
            prints_per_plate=4,
        )
        assert d.machine is None
        assert d.bom_materials == []

    def test_with_all_fields(self):
        d = ModelProductionDefaults(
            model_id=uuid4(),
            sku="MDL-001",
            name="Dragon V2",
            machine="Bambu X1C",
            print_time_minutes=240,
            prints_per_plate=4,
        )
        assert d.machine == "Bambu X1C"
        assert d.print_time_minutes == 240


class TestModelListResponse:
    def test_empty(self):
        r = ModelListResponse(models=[], total=0, skip=0, limit=20)
        assert r.total == 0
        assert r.skip == 0

    def test_paginated(self):
        r = ModelListResponse(models=[], total=100, skip=40, limit=20)
        assert r.skip == 40
