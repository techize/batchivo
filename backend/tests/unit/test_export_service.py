"""Unit tests for ExportService pure helper methods."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.order import OrderStatus
from app.services.export_service import ExportService


@pytest.fixture
def service() -> ExportService:
    """ExportService instance with mocked db and tenant."""
    return ExportService(db=AsyncMock(), tenant=MagicMock())


class TestGenerateHandle:
    """Tests for ExportService._generate_handle."""

    def test_lowercases_text(self, service: ExportService):
        assert service._generate_handle("Dragon") == "dragon"

    def test_replaces_spaces_with_hyphens(self, service: ExportService):
        assert service._generate_handle("Test Dragon") == "test-dragon"

    def test_replaces_special_chars_with_hyphens(self, service: ExportService):
        assert service._generate_handle("Dragon: Ember Edition!") == "dragon-ember-edition"

    def test_strips_leading_trailing_hyphens(self, service: ExportService):
        assert service._generate_handle("!Dragon!") == "dragon"

    def test_collapses_consecutive_specials(self, service: ExportService):
        # multiple non-alphanumeric chars become a single hyphen
        assert service._generate_handle("Dragon -- Ember") == "dragon-ember"

    def test_preserves_numbers(self, service: ExportService):
        assert service._generate_handle("Dragon v2") == "dragon-v2"

    def test_empty_string(self, service: ExportService):
        assert service._generate_handle("") == ""

    def test_all_special_chars(self, service: ExportService):
        assert service._generate_handle("!!!") == ""

    def test_already_valid_handle(self, service: ExportService):
        assert service._generate_handle("frost-dragon") == "frost-dragon"


class TestMapFinancialStatus:
    """Tests for ExportService._map_financial_status."""

    def test_refunded_order_returns_refunded(self, service: ExportService):
        result = service._map_financial_status(OrderStatus.REFUNDED, "completed")
        assert result == "refunded"

    def test_refunded_takes_priority_over_payment_status(self, service: ExportService):
        # Even if payment_status is "pending", REFUNDED order status wins
        result = service._map_financial_status(OrderStatus.REFUNDED, "pending")
        assert result == "refunded"

    def test_completed_payment_returns_paid(self, service: ExportService):
        result = service._map_financial_status(OrderStatus.PROCESSING, "completed")
        assert result == "paid"

    def test_pending_payment_returns_pending(self, service: ExportService):
        result = service._map_financial_status(OrderStatus.PENDING, "pending")
        assert result == "pending"

    def test_unknown_payment_status_defaults_to_paid(self, service: ExportService):
        result = service._map_financial_status(OrderStatus.SHIPPED, "unknown")
        assert result == "paid"

    def test_shipped_with_completed_payment_returns_paid(self, service: ExportService):
        result = service._map_financial_status(OrderStatus.SHIPPED, "completed")
        assert result == "paid"


class TestMapFulfillmentStatus:
    """Tests for ExportService._map_fulfillment_status."""

    def test_pending_returns_empty(self, service: ExportService):
        assert service._map_fulfillment_status(OrderStatus.PENDING) == ""

    def test_processing_returns_empty(self, service: ExportService):
        assert service._map_fulfillment_status(OrderStatus.PROCESSING) == ""

    def test_shipped_returns_fulfilled(self, service: ExportService):
        assert service._map_fulfillment_status(OrderStatus.SHIPPED) == "fulfilled"

    def test_delivered_returns_fulfilled(self, service: ExportService):
        assert service._map_fulfillment_status(OrderStatus.DELIVERED) == "fulfilled"

    def test_cancelled_returns_empty(self, service: ExportService):
        assert service._map_fulfillment_status(OrderStatus.CANCELLED) == ""

    def test_refunded_returns_empty(self, service: ExportService):
        assert service._map_fulfillment_status(OrderStatus.REFUNDED) == ""

    def test_unknown_status_returns_empty(self, service: ExportService):
        assert service._map_fulfillment_status("nonexistent") == ""
