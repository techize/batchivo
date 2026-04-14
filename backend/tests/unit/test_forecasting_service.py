"""Unit tests for ForecastingService pure logic methods."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.services.forecasting_service import DailyDemand, ForecastingService


def _make_service() -> ForecastingService:
    """Create a ForecastingService with a mock DB (not used in pure tests)."""
    return ForecastingService(db=AsyncMock())


def _daily_demand(days_ago: int, quantity: int) -> DailyDemand:
    """Helper to create a DailyDemand with a date relative to now."""
    date = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return DailyDemand(date=date, quantity=quantity)


class TestCalculateStatistics:
    """Tests for ForecastingService._calculate_statistics."""

    def test_empty_history_returns_zeros(self):
        svc = _make_service()
        avg, std, total = svc._calculate_statistics([], analysis_days=30)
        assert avg == 0.0
        assert std == 0.0
        assert total == 0

    def test_single_data_point_no_std_dev(self):
        svc = _make_service()
        history = [_daily_demand(1, 10)]
        avg, std, total = svc._calculate_statistics(history, analysis_days=30)
        assert total == 10
        assert avg == pytest.approx(10 / 30)
        assert std == 0.0  # only one data point

    def test_average_spreads_over_analysis_days(self):
        svc = _make_service()
        # 3 days of sales, 60-day window
        history = [
            _daily_demand(1, 6),
            _daily_demand(2, 6),
            _daily_demand(3, 6),
        ]
        avg, std, total = svc._calculate_statistics(history, analysis_days=60)
        assert total == 18
        assert avg == pytest.approx(18 / 60)

    def test_std_dev_is_non_negative(self):
        svc = _make_service()
        history = [
            _daily_demand(1, 5),
            _daily_demand(5, 15),
            _daily_demand(10, 10),
        ]
        avg, std, total = svc._calculate_statistics(history, analysis_days=30)
        assert std >= 0

    def test_std_dev_zero_for_uniform_sales(self):
        """When every day has identical sales the population std dev is 0."""
        svc = _make_service()
        analysis_days = 5
        # Create one entry per day for all 5 days
        history = [_daily_demand(i, 4) for i in range(1, analysis_days + 1)]
        avg, std, total = svc._calculate_statistics(history, analysis_days=analysis_days)
        assert total == 20
        assert avg == pytest.approx(4.0)
        assert std == pytest.approx(0.0, abs=1e-9)

    def test_total_sold_sums_all_quantities(self):
        svc = _make_service()
        history = [
            _daily_demand(1, 3),
            _daily_demand(2, 7),
            _daily_demand(3, 10),
        ]
        _, _, total = svc._calculate_statistics(history, analysis_days=30)
        assert total == 20


class TestGetConfidenceLevel:
    """Tests for ForecastingService._get_confidence_level."""

    def test_empty_history_is_low(self):
        svc = _make_service()
        assert svc._get_confidence_level([], analysis_days=90) == "low"

    def test_high_confidence_requires_coverage_and_data_points(self):
        svc = _make_service()
        # 30 data points out of 90 days = 33% coverage ≥ 30%, and ≥ 10 points
        history = [_daily_demand(i, 1) for i in range(1, 31)]
        result = svc._get_confidence_level(history, analysis_days=90)
        assert result == "high"

    def test_medium_confidence(self):
        svc = _make_service()
        # 10 data points out of 90 days = 11.1% coverage ≥ 10%, and ≥ 5 points → medium
        # (but < 30% coverage, so not high)
        history = [_daily_demand(i, 1) for i in range(1, 11)]
        result = svc._get_confidence_level(history, analysis_days=90)
        assert result == "medium"

    def test_low_confidence_too_few_points(self):
        svc = _make_service()
        # 3 data points out of 90 = 3.3% coverage, < 5 points
        history = [_daily_demand(i, 1) for i in range(1, 4)]
        result = svc._get_confidence_level(history, analysis_days=90)
        assert result == "low"

    def test_exactly_at_high_threshold(self):
        svc = _make_service()
        # 10 data points out of 30 days = 33% coverage and exactly 10 points
        history = [_daily_demand(i, 1) for i in range(1, 11)]
        result = svc._get_confidence_level(history, analysis_days=30)
        assert result == "high"

    def test_confidence_levels_are_valid_strings(self):
        svc = _make_service()
        valid = {"high", "medium", "low"}
        for count in [0, 3, 6, 30]:
            history = [_daily_demand(i, 1) for i in range(1, count + 1)]
            result = svc._get_confidence_level(history, analysis_days=90)
            assert result in valid
