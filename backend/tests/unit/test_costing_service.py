"""Unit tests for CostingService pure static methods."""

from decimal import Decimal
from types import SimpleNamespace

from app.services.costing import (
    CostingService,
    CircularReferenceError,
    MaxDepthExceededError,
)


class TestCalculateProfit:
    """Tests for CostingService.calculate_profit."""

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
            list_price=Decimal("10.00"),
            make_cost=Decimal("3.00"),
            fee_percentage=Decimal("10"),
        )
        assert result["platform_fee"] == Decimal("1.00")
        assert result["net_revenue"] == Decimal("9.00")
        assert result["profit"] == Decimal("6.00")

    def test_fixed_fee_only(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("10.00"),
            make_cost=Decimal("2.00"),
            fee_fixed=Decimal("0.30"),
        )
        assert result["platform_fee"] == Decimal("0.30")
        assert result["net_revenue"] == Decimal("9.70")
        assert result["profit"] == Decimal("7.70")

    def test_combined_fees(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("100.00"),
            make_cost=Decimal("30.00"),
            fee_percentage=Decimal("5"),
            fee_fixed=Decimal("0.50"),
        )
        assert result["platform_fee"] == Decimal("5.50")
        assert result["net_revenue"] == Decimal("94.50")
        assert result["profit"] == Decimal("64.50")

    def test_zero_price_returns_zero_margin(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("0"),
            make_cost=Decimal("5.00"),
        )
        assert result["margin_percentage"] == Decimal("0")

    def test_loss_scenario(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("5.00"),
            make_cost=Decimal("10.00"),
        )
        assert result["profit"] == Decimal("-5.00")
        assert result["margin_percentage"] < 0

    def test_result_rounded_to_two_decimals(self):
        result = CostingService.calculate_profit(
            list_price=Decimal("3.00"),
            make_cost=Decimal("1.00"),
            fee_percentage=Decimal("10"),
        )
        # All values should be quantized to 0.01
        for key in ("platform_fee", "net_revenue", "profit", "margin_percentage"):
            assert result[key] == result[key].quantize(Decimal("0.01"))


class TestCalculateCostPerGram:
    """Tests for CostingService.calculate_cost_per_gram_from_spool."""

    def test_basic_calculation(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("20.00"),
            initial_weight=Decimal("1000"),
        )
        assert result == Decimal("0.0200")

    def test_none_price_returns_zero(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=None,
            initial_weight=Decimal("1000"),
        )
        assert result == Decimal("0")

    def test_zero_price_returns_zero(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("0"),
            initial_weight=Decimal("1000"),
        )
        assert result == Decimal("0")

    def test_negative_price_returns_zero(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("-5.00"),
            initial_weight=Decimal("1000"),
        )
        assert result == Decimal("0")

    def test_zero_weight_returns_zero(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("20.00"),
            initial_weight=Decimal("0"),
        )
        assert result == Decimal("0")

    def test_result_rounded_to_four_decimals(self):
        result = CostingService.calculate_cost_per_gram_from_spool(
            purchase_price=Decimal("15.00"),
            initial_weight=Decimal("750"),
        )
        assert result == result.quantize(Decimal("0.0001"))


class TestCalculateModelCost:
    """Tests for CostingService.calculate_model_cost."""

    def _model(self, **kwargs):
        """Build a minimal mock model using SimpleNamespace."""
        defaults = {
            "prints_per_plate": 1,
            "materials": [],
            "components": [],
            "labor_hours": None,
            "labor_rate_override": None,
            "overhead_percentage": None,
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_empty_model_zero_cost(self):
        model = self._model()
        breakdown = CostingService.calculate_model_cost(model)
        assert breakdown.total_cost == Decimal("0.000")
        assert breakdown.material_cost == Decimal("0.000")
        assert breakdown.labor_cost == Decimal("0.000")
        assert breakdown.overhead_cost == Decimal("0.000")

    def test_material_cost_calculated(self):
        material = SimpleNamespace(weight_grams=Decimal("100"), cost_per_gram=Decimal("0.02"))
        model = self._model(materials=[material])
        breakdown = CostingService.calculate_model_cost(model)
        assert breakdown.material_cost == Decimal("2.000")

    def test_prints_per_plate_divides_material_cost(self):
        material = SimpleNamespace(weight_grams=Decimal("100"), cost_per_gram=Decimal("0.02"))
        model = self._model(materials=[material], prints_per_plate=4)
        breakdown = CostingService.calculate_model_cost(model)
        # 100g * £0.02/g / 4 prints = £0.50 per print
        assert breakdown.material_cost == Decimal("0.500")

    def test_labor_cost_uses_default_rate(self):
        model = self._model(labor_hours=Decimal("2"))
        # Default labor rate is £10/hr
        breakdown = CostingService.calculate_model_cost(model)
        assert breakdown.labor_cost == Decimal("20.000")

    def test_labor_cost_uses_override_rate(self):
        model = self._model(labor_hours=Decimal("1"), labor_rate_override=Decimal("15"))
        breakdown = CostingService.calculate_model_cost(model)
        assert breakdown.labor_cost == Decimal("15.000")

    def test_tenant_default_labor_rate_applied(self):
        model = self._model(labor_hours=Decimal("2"))
        breakdown = CostingService.calculate_model_cost(
            model, tenant_default_labor_rate=Decimal("12.50")
        )
        assert breakdown.labor_cost == Decimal("25.000")

    def test_overhead_percentage_applied(self):
        material = SimpleNamespace(weight_grams=Decimal("100"), cost_per_gram=Decimal("0.10"))
        # Material cost = £10. Overhead 10% of material+labor = £1
        model = self._model(materials=[material], overhead_percentage=Decimal("10"))
        breakdown = CostingService.calculate_model_cost(model)
        assert breakdown.material_cost == Decimal("10.000")
        assert breakdown.overhead_cost == Decimal("1.000")
        assert breakdown.total_cost == Decimal("11.000")

    def test_component_cost_added(self):
        component = SimpleNamespace(quantity=Decimal("3"), unit_cost=Decimal("1.50"))
        model = self._model(components=[component])
        breakdown = CostingService.calculate_model_cost(model)
        assert breakdown.component_cost == Decimal("4.500")

    def test_all_costs_sum_to_total(self):
        material = SimpleNamespace(weight_grams=Decimal("50"), cost_per_gram=Decimal("0.04"))
        component = SimpleNamespace(quantity=Decimal("2"), unit_cost=Decimal("0.75"))
        model = self._model(
            materials=[material],
            components=[component],
            labor_hours=Decimal("0.5"),
            labor_rate_override=Decimal("12"),
            overhead_percentage=Decimal("5"),
        )
        breakdown = CostingService.calculate_model_cost(model)
        expected_total = (
            breakdown.material_cost
            + breakdown.component_cost
            + breakdown.labor_cost
            + breakdown.overhead_cost
        )
        assert breakdown.total_cost == expected_total.quantize(Decimal("0.001"))


class TestCostingExceptions:
    """Tests for costing error classes."""

    def test_circular_reference_error_message(self):
        from uuid import uuid4
        pid = uuid4()
        visited = {uuid4(), uuid4()}
        err = CircularReferenceError(pid, visited)
        assert str(pid) in str(err)
        assert "Circular reference" in str(err)

    def test_max_depth_exceeded_error_message(self):
        err = MaxDepthExceededError(depth=25, max_depth=20)
        assert "25" in str(err)
        assert "20" in str(err)
