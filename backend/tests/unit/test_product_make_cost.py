"""Unit tests for Product.calculate_make_cost and _calculate_model_cost.

Uses SimpleNamespace to construct model-like objects without SQLAlchemy overhead.
Because calculate_make_cost is an instance method (not @staticmethod or @property),
calls use the unbound pattern: Product.calculate_make_cost(obj, ...).
For composite product tests, the recursive call inside calculate_make_cost requires
child objects to have the method bound — we attach it via types.MethodType.
"""

import types
import uuid
from decimal import Decimal
from types import SimpleNamespace

from app.models.product import Product


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_material(weight_grams, cost_per_gram):
    return SimpleNamespace(
        weight_grams=Decimal(str(weight_grams)),
        cost_per_gram=Decimal(str(cost_per_gram)),
    )


def make_component(quantity, unit_cost):
    return SimpleNamespace(quantity=quantity, unit_cost=Decimal(str(unit_cost)))


def make_model_obj(**kwargs):
    defaults = dict(
        materials=[],
        components=[],
        labor_rate_override=None,
        labor_hours=Decimal("0"),
        overhead_percentage=Decimal("0"),
    )
    return SimpleNamespace(**{**defaults, **kwargs})


def make_product(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        sku="TEST-001",
        product_models=[],
        child_products=[],
        assembly_minutes=0,
        packaging_cost=0.0,
        packaging_consumable=None,
        packaging_quantity=1,
    )
    obj = SimpleNamespace(**{**defaults, **kwargs})
    # Bind the real method so recursive calls work (needed for composite products)
    obj.calculate_make_cost = types.MethodType(Product.calculate_make_cost, obj)
    obj._calculate_model_cost = types.MethodType(Product._calculate_model_cost, obj)
    return obj


def make_product_model(model_obj, quantity=1):
    return SimpleNamespace(model=model_obj, quantity=quantity)


def make_child_product_link(child_product, quantity=1):
    return SimpleNamespace(child_product=child_product, quantity=quantity)


# ---------------------------------------------------------------------------
# Product._calculate_model_cost
# ---------------------------------------------------------------------------


class TestCalculateModelCost:
    def test_no_materials_no_components_no_labor(self):
        product = make_product()
        model = make_model_obj()
        result = Product._calculate_model_cost(product, model, labor_rate=10.0)
        assert result == Decimal("0")

    def test_materials_only(self):
        product = make_product()
        model = make_model_obj(materials=[make_material(100, "0.02")])
        result = Product._calculate_model_cost(product, model, labor_rate=10.0)
        assert result == Decimal("2")

    def test_components_only(self):
        product = make_product()
        model = make_model_obj(components=[make_component(3, "2.00")])
        result = Product._calculate_model_cost(product, model, labor_rate=10.0)
        assert result == Decimal("6")

    def test_labor_uses_default_rate_when_no_override(self):
        product = make_product()
        model = make_model_obj(labor_hours=Decimal("2"), labor_rate_override=None)
        result = Product._calculate_model_cost(product, model, labor_rate=10.0)
        assert result == Decimal("20")

    def test_labor_uses_override_rate(self):
        product = make_product()
        model = make_model_obj(labor_hours=Decimal("1"), labor_rate_override=15.0)
        result = Product._calculate_model_cost(product, model, labor_rate=10.0)
        assert result == Decimal("15")

    def test_overhead_applied_to_subtotal(self):
        product = make_product()
        # material=2, labor=10, subtotal=12, overhead=10% → 1.2 → total=13.2
        model = make_model_obj(
            materials=[make_material(100, "0.02")],
            labor_hours=Decimal("1"),
            overhead_percentage=Decimal("10"),
        )
        result = Product._calculate_model_cost(product, model, labor_rate=10.0)
        assert abs(result - Decimal("13.2")) < Decimal("0.001")

    def test_combined_all_costs(self):
        product = make_product()
        model = make_model_obj(
            materials=[make_material(50, "0.04")],  # 2.00
            components=[make_component(2, "1.00")],  # 2.00
            labor_hours=Decimal("0.5"),  # 5.00 at £10/hr
            overhead_percentage=Decimal("20"),  # 20% of (2+2+5) = 1.80
        )
        result = Product._calculate_model_cost(product, model, labor_rate=10.0)
        assert abs(result - Decimal("10.8")) < Decimal("0.001")


# ---------------------------------------------------------------------------
# Product.calculate_make_cost — basic product
# ---------------------------------------------------------------------------


class TestProductCalculateMakeCost:
    def test_empty_product_all_zeros(self):
        product = make_product()
        result = product.calculate_make_cost()
        assert result["models_cost"] == 0.0
        assert result["child_products_cost"] == 0.0
        assert result["packaging_cost"] == 0.0
        assert result["assembly_cost"] == 0.0
        assert result["total_make_cost"] == 0.0

    def test_assembly_cost_calculated(self):
        # 30 minutes at £10/hr = £5.00
        product = make_product(assembly_minutes=30)
        result = product.calculate_make_cost(labor_rate=10.0)
        assert abs(result["assembly_cost"] - 5.0) < 0.001

    def test_packaging_cost_from_field(self):
        product = make_product(packaging_cost=2.50)
        result = product.calculate_make_cost()
        assert abs(result["packaging_cost"] - 2.50) < 0.001

    def test_packaging_cost_from_consumable_overrides_field(self):
        consumable = SimpleNamespace(unit_cost=Decimal("3.00"))
        product = make_product(
            packaging_consumable=consumable,
            packaging_quantity=2,
            packaging_cost=1.00,  # should be ignored
        )
        result = product.calculate_make_cost()
        assert abs(result["packaging_cost"] - 6.0) < 0.001

    def test_packaging_consumable_with_no_unit_cost_falls_back_to_field(self):
        consumable = SimpleNamespace(unit_cost=None)
        product = make_product(
            packaging_consumable=consumable,
            packaging_cost=1.50,
        )
        result = product.calculate_make_cost()
        assert abs(result["packaging_cost"] - 1.50) < 0.001

    def test_model_cost_included(self):
        model = make_model_obj(materials=[make_material(100, "0.02")])
        pm = make_product_model(model, quantity=1)
        product = make_product(product_models=[pm])
        result = product.calculate_make_cost(labor_rate=10.0)
        assert abs(result["models_cost"] - 2.0) < 0.001

    def test_model_quantity_multiplied(self):
        model = make_model_obj(materials=[make_material(100, "0.02")])
        pm = make_product_model(model, quantity=3)
        product = make_product(product_models=[pm])
        result = product.calculate_make_cost(labor_rate=10.0)
        assert abs(result["models_cost"] - 6.0) < 0.001

    def test_total_is_sum_of_all_components(self):
        model = make_model_obj(materials=[make_material(100, "0.02")])
        pm = make_product_model(model, quantity=1)
        product = make_product(
            product_models=[pm],
            assembly_minutes=30,
            packaging_cost=1.00,
        )
        result = product.calculate_make_cost(labor_rate=10.0)
        expected = (
            result["models_cost"]
            + result["child_products_cost"]
            + result["packaging_cost"]
            + result["assembly_cost"]
        )
        assert abs(result["total_make_cost"] - expected) < 0.001


# ---------------------------------------------------------------------------
# Product.calculate_make_cost — circular reference detection
# ---------------------------------------------------------------------------


class TestProductCalculateMakeCostCircularReference:
    def test_circular_reference_raises_value_error(self):
        product_id = uuid.uuid4()
        product = make_product(id=product_id)

        # Simulate: product is already in its own visited set
        import pytest

        with pytest.raises(ValueError, match="[Cc]ircular"):
            product.calculate_make_cost(visited={product_id})

    def test_no_circular_reference_succeeds(self):
        product = make_product()
        # Should not raise
        result = product.calculate_make_cost()
        assert result is not None


# ---------------------------------------------------------------------------
# Product.calculate_make_cost — composite (bundle) products
# ---------------------------------------------------------------------------


class TestProductCalculateMakeCostComposite:
    def test_child_product_cost_included(self):
        # Child product with a simple model
        child_model = make_model_obj(materials=[make_material(100, "0.02")])
        child_pm = make_product_model(child_model, quantity=1)
        child = make_product(id=uuid.uuid4(), product_models=[child_pm])

        parent = make_product(child_products=[make_child_product_link(child, quantity=1)])
        result = parent.calculate_make_cost(labor_rate=10.0)
        assert abs(result["child_products_cost"] - 2.0) < 0.001

    def test_child_product_quantity_multiplied(self):
        child_model = make_model_obj(materials=[make_material(100, "0.02")])
        child_pm = make_product_model(child_model, quantity=1)
        child = make_product(id=uuid.uuid4(), product_models=[child_pm])

        parent = make_product(child_products=[make_child_product_link(child, quantity=3)])
        result = parent.calculate_make_cost(labor_rate=10.0)
        assert abs(result["child_products_cost"] - 6.0) < 0.001
