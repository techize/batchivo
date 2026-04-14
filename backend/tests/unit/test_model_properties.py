"""Unit tests for computed model properties (pure attribute-based calculations).

Uses SimpleNamespace to construct model-like objects without SQLAlchemy overhead.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.models.consumable import ConsumableType, ConsumableUsage
from app.models.email_verification import EmailVerificationToken
from app.models.model_component import ModelComponent
from app.models.model_material import ModelMaterial
from app.models.print_job import JobStatus, PrintJob
from app.models.printer_connection import ConnectionType, PrinterConnection


# ---------------------------------------------------------------------------
# Helpers — lightweight stand-ins that expose only what the property reads
# ---------------------------------------------------------------------------


def make_consumable_type(**kwargs):
    defaults = dict(quantity_on_hand=10, reorder_point=None, current_cost_per_unit=None)
    return SimpleNamespace(**{**defaults, **kwargs})


def make_consumable_usage(**kwargs):
    defaults = dict(quantity_used=1, cost_at_use=None)
    return SimpleNamespace(**{**defaults, **kwargs})


def make_model_component(**kwargs):
    defaults = dict(quantity=1, unit_cost=Decimal("5.00"), consumable_type=None)
    return SimpleNamespace(**{**defaults, **kwargs})


def make_model_material(**kwargs):
    defaults = dict(weight_grams=50, cost_per_gram=Decimal("0.02"))
    return SimpleNamespace(**{**defaults, **kwargs})


def make_print_job(**kwargs):
    defaults = dict(status=JobStatus.PENDING, model=None, product=None)
    return SimpleNamespace(**{**defaults, **kwargs})


def make_printer_connection(**kwargs):
    defaults = dict(connection_type=ConnectionType.MOONRAKER, serial_number=None, ams_count=0)
    return SimpleNamespace(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# ConsumableType.is_low_stock
# ---------------------------------------------------------------------------


class TestConsumableTypeIsLowStock:
    def test_no_reorder_point_is_false(self):
        obj = make_consumable_type(quantity_on_hand=0, reorder_point=None)
        assert ConsumableType.is_low_stock.fget(obj) is False

    def test_above_reorder_point_is_false(self):
        obj = make_consumable_type(quantity_on_hand=10, reorder_point=5)
        assert ConsumableType.is_low_stock.fget(obj) is False

    def test_at_reorder_point_is_true(self):
        obj = make_consumable_type(quantity_on_hand=5, reorder_point=5)
        assert ConsumableType.is_low_stock.fget(obj) is True

    def test_below_reorder_point_is_true(self):
        obj = make_consumable_type(quantity_on_hand=2, reorder_point=5)
        assert ConsumableType.is_low_stock.fget(obj) is True

    def test_zero_qty_with_reorder_point_is_true(self):
        obj = make_consumable_type(quantity_on_hand=0, reorder_point=1)
        assert ConsumableType.is_low_stock.fget(obj) is True


# ---------------------------------------------------------------------------
# ConsumableType.stock_value
# ---------------------------------------------------------------------------


class TestConsumableTypeStockValue:
    def test_no_cost_returns_zero(self):
        obj = make_consumable_type(quantity_on_hand=10, current_cost_per_unit=None)
        assert ConsumableType.stock_value.fget(obj) == 0.0

    def test_calculates_correctly(self):
        obj = make_consumable_type(quantity_on_hand=10, current_cost_per_unit=Decimal("2.50"))
        assert ConsumableType.stock_value.fget(obj) == 25.0

    def test_zero_quantity(self):
        obj = make_consumable_type(quantity_on_hand=0, current_cost_per_unit=Decimal("5.00"))
        assert ConsumableType.stock_value.fget(obj) == 0.0

    def test_decimal_cost(self):
        obj = make_consumable_type(quantity_on_hand=3, current_cost_per_unit=Decimal("1.99"))
        assert abs(ConsumableType.stock_value.fget(obj) - 5.97) < 0.001


# ---------------------------------------------------------------------------
# ConsumableUsage.total_cost
# ---------------------------------------------------------------------------


class TestConsumableUsageTotalCost:
    def test_no_cost_at_use_returns_zero(self):
        obj = make_consumable_usage(quantity_used=5, cost_at_use=None)
        assert ConsumableUsage.total_cost.fget(obj) == 0.0

    def test_calculates_correctly(self):
        obj = make_consumable_usage(quantity_used=4, cost_at_use=Decimal("2.50"))
        assert ConsumableUsage.total_cost.fget(obj) == 10.0

    def test_fractional_cost(self):
        obj = make_consumable_usage(quantity_used=3, cost_at_use=Decimal("1.33"))
        assert abs(ConsumableUsage.total_cost.fget(obj) - 3.99) < 0.001


# ---------------------------------------------------------------------------
# ModelComponent.total_cost and effective_unit_cost
# ---------------------------------------------------------------------------


class TestModelComponentTotalCost:
    def test_basic_calculation(self):
        obj = make_model_component(quantity=3, unit_cost=Decimal("4.00"))
        assert ModelComponent.total_cost.fget(obj) == 12.0

    def test_zero_quantity(self):
        obj = make_model_component(quantity=0, unit_cost=Decimal("5.00"))
        assert ModelComponent.total_cost.fget(obj) == 0.0

    def test_fractional_unit_cost(self):
        obj = make_model_component(quantity=2, unit_cost=Decimal("3.75"))
        assert ModelComponent.total_cost.fget(obj) == 7.5


class TestModelComponentEffectiveUnitCost:
    def test_no_consumable_uses_unit_cost(self):
        obj = make_model_component(unit_cost=Decimal("5.00"), consumable_type=None)
        assert ModelComponent.effective_unit_cost.fget(obj) == 5.0

    def test_consumable_with_cost_overrides(self):
        consumable = SimpleNamespace(current_cost_per_unit=Decimal("3.00"))
        obj = make_model_component(unit_cost=Decimal("5.00"), consumable_type=consumable)
        assert ModelComponent.effective_unit_cost.fget(obj) == 3.0

    def test_consumable_without_cost_falls_back_to_unit_cost(self):
        consumable = SimpleNamespace(current_cost_per_unit=None)
        obj = make_model_component(unit_cost=Decimal("5.00"), consumable_type=consumable)
        assert ModelComponent.effective_unit_cost.fget(obj) == 5.0


# ---------------------------------------------------------------------------
# ModelMaterial.total_cost
# ---------------------------------------------------------------------------


class TestModelMaterialTotalCost:
    def test_basic_calculation(self):
        obj = make_model_material(weight_grams=100, cost_per_gram=Decimal("0.03"))
        assert abs(ModelMaterial.total_cost.fget(obj) - 3.0) < 0.001

    def test_zero_weight(self):
        obj = make_model_material(weight_grams=0, cost_per_gram=Decimal("0.05"))
        assert ModelMaterial.total_cost.fget(obj) == 0.0

    def test_zero_cost(self):
        obj = make_model_material(weight_grams=50, cost_per_gram=Decimal("0.00"))
        assert ModelMaterial.total_cost.fget(obj) == 0.0


# ---------------------------------------------------------------------------
# PrintJob.is_active and can_be_cancelled
# ---------------------------------------------------------------------------


class TestPrintJobIsActive:
    def test_pending_is_active(self):
        obj = make_print_job(status=JobStatus.PENDING)
        assert PrintJob.is_active.fget(obj) is True

    def test_queued_is_active(self):
        obj = make_print_job(status=JobStatus.QUEUED)
        assert PrintJob.is_active.fget(obj) is True

    def test_printing_is_active(self):
        obj = make_print_job(status=JobStatus.PRINTING)
        assert PrintJob.is_active.fget(obj) is True

    def test_completed_is_not_active(self):
        obj = make_print_job(status=JobStatus.COMPLETED)
        assert PrintJob.is_active.fget(obj) is False

    def test_failed_is_not_active(self):
        obj = make_print_job(status=JobStatus.FAILED)
        assert PrintJob.is_active.fget(obj) is False

    def test_cancelled_is_not_active(self):
        obj = make_print_job(status=JobStatus.CANCELLED)
        assert PrintJob.is_active.fget(obj) is False


class TestPrintJobCanBeCancelled:
    def test_pending_can_be_cancelled(self):
        obj = make_print_job(status=JobStatus.PENDING)
        assert PrintJob.can_be_cancelled.fget(obj) is True

    def test_queued_can_be_cancelled(self):
        obj = make_print_job(status=JobStatus.QUEUED)
        assert PrintJob.can_be_cancelled.fget(obj) is True

    def test_printing_cannot_be_cancelled(self):
        obj = make_print_job(status=JobStatus.PRINTING)
        assert PrintJob.can_be_cancelled.fget(obj) is False

    def test_completed_cannot_be_cancelled(self):
        obj = make_print_job(status=JobStatus.COMPLETED)
        assert PrintJob.can_be_cancelled.fget(obj) is False


# ---------------------------------------------------------------------------
# PrinterConnection.is_bambu, mqtt_topic_prefix, total_ams_slots
# ---------------------------------------------------------------------------


class TestPrinterConnectionIsBambu:
    def test_bambu_lan_is_true(self):
        obj = make_printer_connection(connection_type=ConnectionType.BAMBU_LAN.value)
        assert PrinterConnection.is_bambu.fget(obj) is True

    def test_bambu_cloud_is_true(self):
        obj = make_printer_connection(connection_type=ConnectionType.BAMBU_CLOUD.value)
        assert PrinterConnection.is_bambu.fget(obj) is True

    def test_moonraker_is_false(self):
        obj = make_printer_connection(connection_type=ConnectionType.MOONRAKER.value)
        assert PrinterConnection.is_bambu.fget(obj) is False

    def test_octoprint_is_false(self):
        obj = make_printer_connection(connection_type=ConnectionType.OCTOPRINT.value)
        assert PrinterConnection.is_bambu.fget(obj) is False


class TestPrinterConnectionMqttTopicPrefix:
    def test_bambu_with_serial_returns_prefix(self):
        obj = make_printer_connection(
            connection_type=ConnectionType.BAMBU_LAN.value, serial_number="ABC123"
        )
        # is_bambu reads connection_type; mqtt_topic_prefix reads is_bambu
        # We need to simulate is_bambu returning True for this object
        obj.is_bambu = True
        assert PrinterConnection.mqtt_topic_prefix.fget(obj) == "device/ABC123"

    def test_bambu_without_serial_returns_none(self):
        obj = make_printer_connection(
            connection_type=ConnectionType.BAMBU_LAN.value, serial_number=None
        )
        obj.is_bambu = True
        assert PrinterConnection.mqtt_topic_prefix.fget(obj) is None

    def test_non_bambu_returns_none(self):
        obj = make_printer_connection(
            connection_type=ConnectionType.MOONRAKER.value, serial_number="SER123"
        )
        obj.is_bambu = False
        assert PrinterConnection.mqtt_topic_prefix.fget(obj) is None


class TestPrinterConnectionTotalAmsSlots:
    def test_zero_ams(self):
        obj = make_printer_connection(ams_count=0)
        assert PrinterConnection.total_ams_slots.fget(obj) == 0

    def test_one_ams_unit_gives_four_slots(self):
        obj = make_printer_connection(ams_count=1)
        assert PrinterConnection.total_ams_slots.fget(obj) == 4

    def test_two_ams_units_give_eight_slots(self):
        obj = make_printer_connection(ams_count=2)
        assert PrinterConnection.total_ams_slots.fget(obj) == 8


# ---------------------------------------------------------------------------
# EmailVerificationToken.is_expired, is_used, is_valid
# ---------------------------------------------------------------------------


def make_token(**kwargs):
    now = datetime.now(timezone.utc)
    defaults = dict(
        expires_at=now + timedelta(hours=1),
        used_at=None,
    )
    return SimpleNamespace(**{**defaults, **kwargs})


class TestEmailVerificationTokenIsExpired:
    def test_future_expires_at_is_not_expired(self):
        obj = make_token(expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
        assert EmailVerificationToken.is_expired.fget(obj) is False

    def test_past_expires_at_is_expired(self):
        obj = make_token(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        assert EmailVerificationToken.is_expired.fget(obj) is True

    def test_far_future_is_not_expired(self):
        obj = make_token(expires_at=datetime.now(timezone.utc) + timedelta(days=365))
        assert EmailVerificationToken.is_expired.fget(obj) is False


class TestEmailVerificationTokenIsUsed:
    def test_used_at_none_is_not_used(self):
        obj = make_token(used_at=None)
        assert EmailVerificationToken.is_used.fget(obj) is False

    def test_used_at_set_is_used(self):
        obj = make_token(used_at=datetime.now(timezone.utc))
        assert EmailVerificationToken.is_used.fget(obj) is True


class TestEmailVerificationTokenIsValid:
    def test_not_expired_and_not_used_is_valid(self):
        obj = make_token(
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used_at=None,
        )
        # Simulate is_expired=False and is_used=False
        obj.is_expired = False
        obj.is_used = False
        assert EmailVerificationToken.is_valid.fget(obj) is True

    def test_expired_is_not_valid(self):
        obj = make_token(
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            used_at=None,
        )
        obj.is_expired = True
        obj.is_used = False
        assert EmailVerificationToken.is_valid.fget(obj) is False

    def test_used_is_not_valid(self):
        obj = make_token(
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used_at=datetime.now(timezone.utc),
        )
        obj.is_expired = False
        obj.is_used = True
        assert EmailVerificationToken.is_valid.fget(obj) is False

    def test_expired_and_used_is_not_valid(self):
        obj = make_token(
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            used_at=datetime.now(timezone.utc),
        )
        obj.is_expired = True
        obj.is_used = True
        assert EmailVerificationToken.is_valid.fget(obj) is False
