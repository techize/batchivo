"""Unit tests for SalesChannel.calculate_platform_fee and
ProductPricing.calculate_profit.

Uses SimpleNamespace + unbound method calls (no SQLAlchemy session needed).
"""

from decimal import Decimal
from types import SimpleNamespace

from app.models.product_pricing import ProductPricing
from app.models.sales_channel import SalesChannel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_channel(**kwargs):
    defaults = dict(fee_percentage=Decimal("0"), fee_fixed=Decimal("0"))
    return SimpleNamespace(**{**defaults, **kwargs})


def make_pricing(list_price, channel, **kwargs):
    obj = SimpleNamespace(list_price=Decimal(str(list_price)), sales_channel=channel, **kwargs)
    return obj


# ---------------------------------------------------------------------------
# SalesChannel.calculate_platform_fee
# ---------------------------------------------------------------------------


class TestSalesChannelCalculatePlatformFee:
    def test_no_fees_returns_zero(self):
        channel = make_channel(fee_percentage=Decimal("0"), fee_fixed=Decimal("0"))
        assert SalesChannel.calculate_platform_fee(channel, 100.0) == 0.0

    def test_percentage_fee_only(self):
        channel = make_channel(fee_percentage=Decimal("5"), fee_fixed=Decimal("0"))
        assert abs(SalesChannel.calculate_platform_fee(channel, 100.0) - 5.0) < 0.001

    def test_fixed_fee_only(self):
        channel = make_channel(fee_percentage=Decimal("0"), fee_fixed=Decimal("0.20"))
        assert abs(SalesChannel.calculate_platform_fee(channel, 100.0) - 0.20) < 0.001

    def test_both_fees_combined(self):
        # 6.5% + £0.30 of £50 = 3.25 + 0.30 = 3.55
        channel = make_channel(fee_percentage=Decimal("6.5"), fee_fixed=Decimal("0.30"))
        assert abs(SalesChannel.calculate_platform_fee(channel, 50.0) - 3.55) < 0.001

    def test_etsy_like_fees(self):
        # Etsy: 6.5% + £0.20 listing equivalent
        channel = make_channel(fee_percentage=Decimal("6.5"), fee_fixed=Decimal("0.20"))
        result = SalesChannel.calculate_platform_fee(channel, 20.0)
        assert abs(result - 1.50) < 0.001  # 1.30 + 0.20

    def test_zero_list_price(self):
        channel = make_channel(fee_percentage=Decimal("10"), fee_fixed=Decimal("0.50"))
        result = SalesChannel.calculate_platform_fee(channel, 0.0)
        assert abs(result - 0.50) < 0.001

    def test_high_percentage(self):
        channel = make_channel(fee_percentage=Decimal("100"), fee_fixed=Decimal("0"))
        result = SalesChannel.calculate_platform_fee(channel, 25.0)
        assert abs(result - 25.0) < 0.001


# ---------------------------------------------------------------------------
# ProductPricing.calculate_profit
# ---------------------------------------------------------------------------


class TestProductPricingCalculateProfit:
    def test_basic_profit_no_fees(self):
        channel = make_channel(fee_percentage=Decimal("0"), fee_fixed=Decimal("0"))
        channel.calculate_platform_fee = lambda price: SalesChannel.calculate_platform_fee(
            channel, price
        )
        pricing = make_pricing(20.0, channel)
        result = ProductPricing.calculate_profit(pricing, make_cost=5.0)
        assert abs(result["list_price"] - 20.0) < 0.001
        assert abs(result["platform_fee"] - 0.0) < 0.001
        assert abs(result["net_revenue"] - 20.0) < 0.001
        assert abs(result["profit"] - 15.0) < 0.001
        assert abs(result["margin_percentage"] - 75.0) < 0.001

    def test_with_percentage_fee(self):
        channel = make_channel(fee_percentage=Decimal("10"), fee_fixed=Decimal("0"))
        channel.calculate_platform_fee = lambda price: SalesChannel.calculate_platform_fee(
            channel, price
        )
        pricing = make_pricing(100.0, channel)
        result = ProductPricing.calculate_profit(pricing, make_cost=30.0)
        assert abs(result["platform_fee"] - 10.0) < 0.001
        assert abs(result["net_revenue"] - 90.0) < 0.001
        assert abs(result["profit"] - 60.0) < 0.001

    def test_with_fixed_fee(self):
        channel = make_channel(fee_percentage=Decimal("0"), fee_fixed=Decimal("0.50"))
        channel.calculate_platform_fee = lambda price: SalesChannel.calculate_platform_fee(
            channel, price
        )
        pricing = make_pricing(10.0, channel)
        result = ProductPricing.calculate_profit(pricing, make_cost=3.0)
        assert abs(result["platform_fee"] - 0.50) < 0.001
        assert abs(result["net_revenue"] - 9.50) < 0.001
        assert abs(result["profit"] - 6.50) < 0.001

    def test_negative_profit_when_cost_exceeds_revenue(self):
        channel = make_channel(fee_percentage=Decimal("0"), fee_fixed=Decimal("0"))
        channel.calculate_platform_fee = lambda price: SalesChannel.calculate_platform_fee(
            channel, price
        )
        pricing = make_pricing(5.0, channel)
        result = ProductPricing.calculate_profit(pricing, make_cost=10.0)
        assert result["profit"] < 0

    def test_zero_list_price_margin_is_zero(self):
        channel = make_channel(fee_percentage=Decimal("0"), fee_fixed=Decimal("0"))
        channel.calculate_platform_fee = lambda price: SalesChannel.calculate_platform_fee(
            channel, price
        )
        pricing = make_pricing(0.0, channel)
        result = ProductPricing.calculate_profit(pricing, make_cost=0.0)
        assert result["margin_percentage"] == 0.0

    def test_result_contains_all_keys(self):
        channel = make_channel(fee_percentage=Decimal("5"), fee_fixed=Decimal("0"))
        channel.calculate_platform_fee = lambda price: SalesChannel.calculate_platform_fee(
            channel, price
        )
        pricing = make_pricing(50.0, channel)
        result = ProductPricing.calculate_profit(pricing, make_cost=10.0)
        assert set(result.keys()) == {
            "list_price",
            "platform_fee",
            "net_revenue",
            "profit",
            "margin_percentage",
        }
