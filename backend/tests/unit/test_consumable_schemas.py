"""
Tests for Consumable Inventory Pydantic schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.consumable import (
    ConsumablePurchaseCreate,
    ConsumablePurchaseUpdate,
    ConsumableTypeBase,
    ConsumableTypeCreate,
    ConsumableTypeUpdate,
    ConsumableUsageCreate,
    StockAdjustment,
)


class TestConsumableTypeBase:
    def _valid(self, **kwargs) -> dict:
        defaults = {"sku": "MAG-6MM", "name": "6mm Magnets"}
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        c = ConsumableTypeBase(**self._valid())
        assert c.sku == "MAG-6MM"
        assert c.unit_of_measure == "each"
        assert c.quantity_on_hand == 0
        assert c.is_active is True

    def test_sku_empty_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(sku=""))

    def test_sku_too_long_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(sku="S" * 51))

    def test_name_empty_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(name=""))

    def test_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(name="N" * 201))

    def test_current_cost_per_unit_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(current_cost_per_unit=-0.01))

    def test_current_cost_per_unit_zero_accepted(self):
        c = ConsumableTypeBase(**self._valid(current_cost_per_unit=0.0))
        assert c.current_cost_per_unit == 0.0

    def test_quantity_on_hand_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(quantity_on_hand=-1))

    def test_quantity_on_hand_zero_accepted(self):
        c = ConsumableTypeBase(**self._valid(quantity_on_hand=0))
        assert c.quantity_on_hand == 0

    def test_reorder_point_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(reorder_point=-1))

    def test_reorder_quantity_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(reorder_quantity=-1))

    def test_typical_lead_days_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(typical_lead_days=-1))

    def test_typical_lead_days_zero_accepted(self):
        c = ConsumableTypeBase(**self._valid(typical_lead_days=0))
        assert c.typical_lead_days == 0

    def test_category_max_100(self):
        c = ConsumableTypeBase(**self._valid(category="C" * 100))
        assert len(c.category) == 100

    def test_category_too_long_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeBase(**self._valid(category="C" * 101))


class TestConsumableTypeCreate:
    def test_inherits_from_base(self):
        c = ConsumableTypeCreate(sku="INS-M3", name="M3 Inserts")
        assert c.sku == "INS-M3"


class TestConsumableTypeUpdate:
    def test_all_optional(self):
        u = ConsumableTypeUpdate()
        assert u.sku is None
        assert u.name is None
        assert u.is_active is None

    def test_partial_update(self):
        u = ConsumableTypeUpdate(is_active=False, quantity_on_hand=50)
        assert u.is_active is False
        assert u.quantity_on_hand == 50

    def test_sku_empty_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeUpdate(sku="")

    def test_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumableTypeUpdate(current_cost_per_unit=-1.0)


class TestConsumablePurchaseCreate:
    def _valid(self, **kwargs) -> dict:
        defaults = {
            "consumable_type_id": uuid4(),
            "quantity_purchased": 100,
            "total_cost": 4.99,
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        p = ConsumablePurchaseCreate(**self._valid())
        assert p.quantity_purchased == 100

    def test_quantity_zero_raises(self):
        with pytest.raises(ValidationError):
            ConsumablePurchaseCreate(**self._valid(quantity_purchased=0))

    def test_quantity_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumablePurchaseCreate(**self._valid(quantity_purchased=-1))

    def test_total_cost_zero_accepted(self):
        p = ConsumablePurchaseCreate(**self._valid(total_cost=0.0))
        assert p.total_cost == 0.0

    def test_total_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumablePurchaseCreate(**self._valid(total_cost=-0.01))

    def test_supplier_max_200(self):
        p = ConsumablePurchaseCreate(**self._valid(supplier="S" * 200))
        assert len(p.supplier) == 200

    def test_supplier_too_long_raises(self):
        with pytest.raises(ValidationError):
            ConsumablePurchaseCreate(**self._valid(supplier="S" * 201))


class TestConsumablePurchaseUpdate:
    def test_all_optional(self):
        u = ConsumablePurchaseUpdate()
        assert u.quantity_purchased is None
        assert u.total_cost is None

    def test_quantity_zero_raises(self):
        with pytest.raises(ValidationError):
            ConsumablePurchaseUpdate(quantity_purchased=0)

    def test_cost_negative_raises(self):
        with pytest.raises(ValidationError):
            ConsumablePurchaseUpdate(total_cost=-1.0)


class TestConsumableUsageCreate:
    def test_valid(self):
        u = ConsumableUsageCreate(
            consumable_type_id=uuid4(),
            quantity_used=5,
        )
        assert u.quantity_used == 5
        assert u.usage_type == "production"

    def test_negative_quantity_allowed(self):
        # Negative for returns/adjustments per docstring
        u = ConsumableUsageCreate(
            consumable_type_id=uuid4(),
            quantity_used=-3,
        )
        assert u.quantity_used == -3

    def test_usage_type_max_50(self):
        u = ConsumableUsageCreate(
            consumable_type_id=uuid4(),
            quantity_used=1,
            usage_type="adjustment",
        )
        assert u.usage_type == "adjustment"


class TestStockAdjustment:
    def test_positive_adjustment(self):
        a = StockAdjustment(quantity_adjustment=10, reason="Restocked from supplier")
        assert a.quantity_adjustment == 10

    def test_negative_adjustment(self):
        a = StockAdjustment(quantity_adjustment=-5, reason="Damaged goods removed")
        assert a.quantity_adjustment == -5

    def test_reason_empty_raises(self):
        with pytest.raises(ValidationError):
            StockAdjustment(quantity_adjustment=1, reason="")

    def test_reason_too_long_raises(self):
        with pytest.raises(ValidationError):
            StockAdjustment(quantity_adjustment=1, reason="r" * 201)

    def test_reason_max_200(self):
        a = StockAdjustment(quantity_adjustment=1, reason="r" * 200)
        assert len(a.reason) == 200

    def test_notes_optional(self):
        a = StockAdjustment(quantity_adjustment=1, reason="Test")
        assert a.notes is None
