"""Unit tests for pure/static CostingService methods.

Uses SimpleNamespace to construct model-like objects without SQLAlchemy overhead.
Tests calculate_model_cost, calculate_profit, and calculate_cost_per_gram_from_spool.
"""

from decimal import Decimal
from types import SimpleNamespace

from app.services.costing import CostingService


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


def make_model(**kwargs):
    defaults = dict(
        prints_per_plate=1,
        materials=[],
        components=[],
        labor_rate_override=None,
        labor_hours=None,
        overhead_percentage=None,
    )
    return SimpleNamespace(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# CostingService.calculate_model_cost — material cost
# ---------------------------------------------------------------------------


class TestCalculateModelCostMaterials:
    def test_no_materials_zero_material_cost(self):
        model = make_model()
        result = CostingService.calculate_model_cost(model)
        assert result.material_cost == Decimal("0.000")

    def test_single_material(self):
        model = make_model(materials=[make_material(100, "0.03")])
        result = CostingService.calculate_model_cost(model)
        assert result.material_cost == Decimal("3.000")

    def test_multiple_materials_summed(self):
        model = make_model(
            materials=[
                make_material(100, "0.02"),
                make_material(50, "0.04"),
            ]
        )
        result = CostingService.calculate_model_cost(model)
        # 100*0.02 + 50*0.04 = 2.00 + 2.00 = 4.00
        assert result.material_cost == Decimal("4.000")

    def test_material_cost_divided_by_prints_per_plate(self):
        # 2 prints per plate — plate cost is divided between them
        model = make_model(
            prints_per_plate=2,
            materials=[make_material(100, "0.04")],  # plate cost = 4.00
        )
        result = CostingService.calculate_model_cost(model)
        assert result.material_cost == Decimal("2.000")

    def test_zero_prints_per_plate_treated_as_one(self):
        model = make_model(
            prints_per_plate=0,
            materials=[make_material(50, "0.02")],
        )
        result = CostingService.calculate_model_cost(model)
        assert result.material_cost == Decimal("1.000")


# ---------------------------------------------------------------------------
# CostingService.calculate_model_cost — component cost
# ---------------------------------------------------------------------------


class TestCalculateModelCostComponents:
    def test_no_components_zero_cost(self):
        model = make_model()
        result = CostingService.calculate_model_cost(model)
        assert result.component_cost == Decimal("0.000")

    def test_single_component(self):
        model = make_model(components=[make_component(3, "2.00")])
        result = CostingService.calculate_model_cost(model)
        assert result.component_cost == Decimal("6.000")

    def test_multiple_components_summed(self):
        model = make_model(components=[make_component(2, "3.00"), make_component(5, "1.50")])
        result = CostingService.calculate_model_cost(model)
        # 6.00 + 7.50 = 13.50
        assert result.component_cost == Decimal("13.500")


# ---------------------------------------------------------------------------
# CostingService.calculate_model_cost — labor cost
# ---------------------------------------------------------------------------


class TestCalculateModelCostLabor:
    def test_no_labor_hours_zero_labor_cost(self):
        model = make_model()
        result = CostingService.calculate_model_cost(model)
        assert result.labor_cost == Decimal("0.000")

    def test_labor_cost_with_default_rate(self):
        # Default labor rate is £10/hour
        model = make_model(labor_hours=Decimal("2"))
        result = CostingService.calculate_model_cost(model)
        assert result.labor_cost == Decimal("20.000")

    def test_labor_cost_with_override_rate(self):
        model = make_model(labor_hours=Decimal("1.5"), labor_rate_override=Decimal("15.00"))
        result = CostingService.calculate_model_cost(model)
        assert result.labor_cost == Decimal("22.500")

    def test_tenant_default_labor_rate_used_when_no_override(self):
        model = make_model(labor_hours=Decimal("1"))
        result = CostingService.calculate_model_cost(
            model, tenant_default_labor_rate=Decimal("12.00")
        )
        assert result.labor_cost == Decimal("12.000")

    def test_model_override_takes_precedence_over_tenant_default(self):
        model = make_model(labor_hours=Decimal("1"), labor_rate_override=Decimal("20.00"))
        result = CostingService.calculate_model_cost(
            model, tenant_default_labor_rate=Decimal("12.00")
        )
        assert result.labor_cost == Decimal("20.000")


# ---------------------------------------------------------------------------
# CostingService.calculate_model_cost — overhead cost
# ---------------------------------------------------------------------------


class TestCalculateModelCostOverhead:
    def test_no_overhead_zero_overhead_cost(self):
        model = make_model(materials=[make_material(100, "0.02")])
        result = CostingService.calculate_model_cost(model)
        assert result.overhead_cost == Decimal("0.000")

    def test_overhead_percentage_applied_to_material_and_labor(self):
        # material=2.00, labor=10.00, overhead=20% → 2.40
        model = make_model(
            materials=[make_material(100, "0.02")],
            labor_hours=Decimal("1"),
            overhead_percentage=Decimal("20"),
        )
        result = CostingService.calculate_model_cost(model)
        assert result.overhead_cost == Decimal("2.400")

    def test_tenant_default_overhead_used_when_no_model_override(self):
        model = make_model(materials=[make_material(100, "0.02")])
        result = CostingService.calculate_model_cost(
            model, tenant_default_overhead_pct=Decimal("10")
        )
        assert result.overhead_cost == Decimal("0.200")


# ---------------------------------------------------------------------------
# CostingService.calculate_model_cost — total cost
# ---------------------------------------------------------------------------


class TestCalculateModelCostTotal:
    def test_total_is_sum_of_all_components(self):
        model = make_model(
            materials=[make_material(100, "0.02")],
            components=[make_component(1, "3.00")],
            labor_hours=Decimal("1"),
            overhead_percentage=Decimal("10"),
        )
        result = CostingService.calculate_model_cost(model)
        # material=2.00, component=3.00, labor=10.00, overhead=1.20 → total=16.20
        assert (
            result.total_cost
            == result.material_cost
            + result.component_cost
            + result.labor_cost
            + result.overhead_cost
        )

    def test_empty_model_all_zeros(self):
        model = make_model()
        result = CostingService.calculate_model_cost(model)
        assert result.total_cost == Decimal("0.000")


# ---------------------------------------------------------------------------
# CostingService.calculate_profit
# ---------------------------------------------------------------------------


class TestCalculateProfit:
    def test_basic_profit_no_fees(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("20.00"),
            make_cost=Decimal("5.00"),
        )
        assert result["platform_fee"] == Decimal("0.00")
        assert result["net_revenue"] == Decimal("20.00")
        assert result["profit"] == Decimal("15.00")
        assert result["margin_percentage"] == Decimal("75.00")

    def test_percentage_fee_only(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("100.00"),
            make_cost=Decimal("20.00"),
            fee_percentage=Decimal("10"),
        )
        assert result["platform_fee"] == Decimal("10.00")
        assert result["net_revenue"] == Decimal("90.00")
        assert result["profit"] == Decimal("70.00")

    def test_fixed_fee_only(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("50.00"),
            make_cost=Decimal("10.00"),
            fee_fixed=Decimal("0.20"),
        )
        assert result["platform_fee"] == Decimal("0.20")
        assert result["net_revenue"] == Decimal("49.80")
        assert result["profit"] == Decimal("39.80")

    def test_both_fees_combined(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("100.00"),
            make_cost=Decimal("30.00"),
            fee_percentage=Decimal("5"),
            fee_fixed=Decimal("0.30"),
        )
        assert result["platform_fee"] == Decimal("5.30")
        assert result["net_revenue"] == Decimal("94.70")
        assert result["profit"] == Decimal("64.70")

    def test_zero_list_price_margin_is_zero(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("0.00"),
            make_cost=Decimal("5.00"),
        )
        assert result["margin_percentage"] == Decimal("0.00")

    def test_negative_profit_when_cost_exceeds_revenue(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("10.00"),
            make_cost=Decimal("15.00"),
        )
        assert result["profit"] == Decimal("-5.00")

    def test_margin_percentage_calculated_correctly(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("50.00"),
            make_cost=Decimal("25.00"),
        )
        # profit=25, margin=50%
        assert result["margin_percentage"] == Decimal("50.00")

    def test_result_rounded_to_two_decimal_places(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("33.33"),
            make_cost=Decimal("10.00"),
        )
        # All values should have exactly 2 decimal places
        for key in ("platform_fee", "net_revenue", "profit", "margin_percentage"):
            assert result[key] == result[key].quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# CostingService.calculate_cost_per_gram_from_spool
# ---------------------------------------------------------------------------


class TestCalculateCostPerGramFromSpool:
    def test_basic_calculation(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("20.00"),
            initial_weight=Decimal("1000"),
        )
        assert result == Decimal("0.0200")

    def test_none_purchase_price_returns_zero(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=None,
            initial_weight=Decimal("1000"),
        )
        assert result == Decimal("0")

    def test_zero_purchase_price_returns_zero(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("0"),
            initial_weight=Decimal("1000"),
        )
        assert result == Decimal("0")

    def test_zero_initial_weight_returns_zero(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("20.00"),
            initial_weight=Decimal("0"),
        )
        assert result == Decimal("0")

    def test_result_has_four_decimal_places(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("15.00"),
            initial_weight=Decimal("750"),
        )
        assert result == result.quantize(Decimal("0.0001"))
        assert result == Decimal("0.0200")

    def test_fractional_result(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("17.99"),
            initial_weight=Decimal("1000"),
        )
        assert result == Decimal("0.0180")  # quantized to 4dp
