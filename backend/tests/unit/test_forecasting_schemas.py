"""
Tests for inventory forecasting Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.forecasting import (
    ForecastSettingsRequest,
    ReorderRecommendationsListResponse,
    StockHealthResponse,
)


class TestForecastSettingsRequest:
    def test_defaults(self):
        s = ForecastSettingsRequest()
        assert s.lead_time_days == 7
        assert s.analysis_days == 90
        assert s.forecast_days == 30

    # --- lead_time_days ---
    def test_lead_time_minimum_1(self):
        s = ForecastSettingsRequest(lead_time_days=1)
        assert s.lead_time_days == 1

    def test_lead_time_zero_raises(self):
        with pytest.raises(ValidationError):
            ForecastSettingsRequest(lead_time_days=0)

    def test_lead_time_maximum_90(self):
        s = ForecastSettingsRequest(lead_time_days=90)
        assert s.lead_time_days == 90

    def test_lead_time_above_90_raises(self):
        with pytest.raises(ValidationError):
            ForecastSettingsRequest(lead_time_days=91)

    # --- analysis_days ---
    def test_analysis_minimum_7(self):
        s = ForecastSettingsRequest(analysis_days=7)
        assert s.analysis_days == 7

    def test_analysis_below_minimum_raises(self):
        with pytest.raises(ValidationError):
            ForecastSettingsRequest(analysis_days=6)

    def test_analysis_maximum_365(self):
        s = ForecastSettingsRequest(analysis_days=365)
        assert s.analysis_days == 365

    def test_analysis_above_maximum_raises(self):
        with pytest.raises(ValidationError):
            ForecastSettingsRequest(analysis_days=366)

    # --- forecast_days ---
    def test_forecast_minimum_1(self):
        s = ForecastSettingsRequest(forecast_days=1)
        assert s.forecast_days == 1

    def test_forecast_zero_raises(self):
        with pytest.raises(ValidationError):
            ForecastSettingsRequest(forecast_days=0)

    def test_forecast_maximum_365(self):
        s = ForecastSettingsRequest(forecast_days=365)
        assert s.forecast_days == 365

    def test_forecast_above_maximum_raises(self):
        with pytest.raises(ValidationError):
            ForecastSettingsRequest(forecast_days=366)

    def test_all_fields_set(self):
        s = ForecastSettingsRequest(lead_time_days=14, analysis_days=60, forecast_days=14)
        assert s.lead_time_days == 14
        assert s.analysis_days == 60
        assert s.forecast_days == 14


class TestReorderRecommendationsListResponse:
    def test_valid_empty(self):
        r = ReorderRecommendationsListResponse(items=[], total=0, critical_count=0, soon_count=0)
        assert r.items == []
        assert r.critical_count == 0

    def test_counts(self):
        r = ReorderRecommendationsListResponse(items=[], total=10, critical_count=3, soon_count=4)
        assert r.critical_count == 3
        assert r.soon_count == 4


class TestStockHealthResponse:
    def test_valid_empty(self):
        r = StockHealthResponse(items=[], total=0)
        assert r.items == []
        assert r.summary == {}

    def test_summary_with_data(self):
        r = StockHealthResponse(
            items=[],
            total=5,
            summary={"critical": 1, "adequate": 4},
        )
        assert r.summary["critical"] == 1
