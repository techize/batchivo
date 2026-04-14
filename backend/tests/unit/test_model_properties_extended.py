"""Unit tests for additional computed model properties.

Covers Spool, ProductionRun, ProductionRunMaterial, ProductionRunPlate,
InventoryTransaction, AMSSlotMapping, and Printer using the SimpleNamespace
+ fget pattern (no SQLAlchemy session needed).
"""

from decimal import Decimal
from types import SimpleNamespace

from app.models.ams_slot_mapping import AMSSlotMapping
from app.models.inventory_transaction import InventoryTransaction
from app.models.printer import Printer
from app.models.production_run import ProductionRun, ProductionRunMaterial
from app.models.production_run_plate import ProductionRunPlate
from app.models.spool import Spool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_spool(**kwargs):
    defaults = dict(
        current_weight=Decimal("500"),
        initial_weight=Decimal("1000"),
        purchase_price=None,
    )
    return SimpleNamespace(**{**defaults, **kwargs})


def make_production_run(**kwargs):
    defaults = dict(
        total_plates=0,
        completed_plates=0,
        product=None,
        items=[],
    )
    return SimpleNamespace(**{**defaults, **kwargs})


def make_production_run_material(**kwargs):
    defaults = dict(
        estimated_model_weight_grams=Decimal("100"),
        estimated_flushed_grams=Decimal("0"),
        estimated_tower_grams=Decimal("0"),
        spool_weight_before_grams=None,
        spool_weight_after_grams=None,
        actual_model_weight_grams=None,
        actual_flushed_grams=None,
        actual_tower_grams=None,
        cost_per_gram=Decimal("0.02"),
    )
    return SimpleNamespace(**{**defaults, **kwargs})


def make_plate(**kwargs):
    defaults = dict(
        status="pending",
        quantity=1,
        prints_per_plate=1,
        successful_prints=0,
        print_time_minutes=None,
        estimated_material_weight_grams=None,
    )
    return SimpleNamespace(**{**defaults, **kwargs})


def make_inventory_transaction(**kwargs):
    defaults = dict(weight_change=Decimal("10"))
    return SimpleNamespace(**{**defaults, **kwargs})


def make_ams_slot(**kwargs):
    defaults = dict(ams_id=0, tray_id=0, last_reported_color=None)
    return SimpleNamespace(**{**defaults, **kwargs})


def make_printer(**kwargs):
    defaults = dict(bed_size_x_mm=None, bed_size_y_mm=None, bed_size_z_mm=None)
    return SimpleNamespace(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Spool.remaining_weight
# ---------------------------------------------------------------------------


class TestSpoolRemainingWeight:
    def test_returns_float_of_current_weight(self):
        obj = make_spool(current_weight=Decimal("750"))
        assert Spool.remaining_weight.fget(obj) == 750.0

    def test_zero_current_weight(self):
        obj = make_spool(current_weight=Decimal("0"))
        assert Spool.remaining_weight.fget(obj) == 0.0

    def test_fractional_weight(self):
        obj = make_spool(current_weight=Decimal("123.45"))
        assert abs(Spool.remaining_weight.fget(obj) - 123.45) < 0.001


# ---------------------------------------------------------------------------
# Spool.remaining_percentage
# ---------------------------------------------------------------------------


class TestSpoolRemainingPercentage:
    def test_half_full(self):
        obj = make_spool(current_weight=Decimal("500"), initial_weight=Decimal("1000"))
        assert abs(Spool.remaining_percentage.fget(obj) - 50.0) < 0.001

    def test_full_spool(self):
        obj = make_spool(current_weight=Decimal("1000"), initial_weight=Decimal("1000"))
        assert abs(Spool.remaining_percentage.fget(obj) - 100.0) < 0.001

    def test_empty_spool(self):
        obj = make_spool(current_weight=Decimal("0"), initial_weight=Decimal("1000"))
        assert Spool.remaining_percentage.fget(obj) == 0.0

    def test_zero_initial_weight_returns_zero(self):
        obj = make_spool(current_weight=Decimal("100"), initial_weight=Decimal("0"))
        assert Spool.remaining_percentage.fget(obj) == 0.0


# ---------------------------------------------------------------------------
# Spool.cost_per_gram
# ---------------------------------------------------------------------------


class TestSpoolCostPerGram:
    def test_no_purchase_price_returns_none(self):
        obj = make_spool(purchase_price=None, initial_weight=Decimal("1000"))
        assert Spool.cost_per_gram.fget(obj) is None

    def test_calculates_correctly(self):
        obj = make_spool(purchase_price=Decimal("20.00"), initial_weight=Decimal("1000"))
        assert abs(Spool.cost_per_gram.fget(obj) - 0.02) < 0.0001

    def test_zero_initial_weight_returns_none(self):
        obj = make_spool(purchase_price=Decimal("20.00"), initial_weight=Decimal("0"))
        assert Spool.cost_per_gram.fget(obj) is None


# ---------------------------------------------------------------------------
# Spool.is_low_stock
# ---------------------------------------------------------------------------


class TestSpoolIsLowStock:
    def test_above_threshold_is_not_low(self):
        # remaining_percentage = 50%, threshold default 20%
        obj = make_spool(current_weight=Decimal("500"), initial_weight=Decimal("1000"))
        obj.remaining_percentage = 50.0
        assert Spool.is_low_stock.fget(obj) is False

    def test_below_threshold_is_low(self):
        obj = make_spool(current_weight=Decimal("100"), initial_weight=Decimal("1000"))
        obj.remaining_percentage = 10.0
        assert Spool.is_low_stock.fget(obj) is True

    def test_at_threshold_is_not_low(self):
        # < threshold, not <=, so 20.0 is NOT low
        obj = make_spool(current_weight=Decimal("200"), initial_weight=Decimal("1000"))
        obj.remaining_percentage = 20.0
        assert Spool.is_low_stock.fget(obj) is False

    def test_just_below_threshold_is_low(self):
        obj = make_spool(current_weight=Decimal("199"), initial_weight=Decimal("1000"))
        obj.remaining_percentage = 19.9
        assert Spool.is_low_stock.fget(obj) is True


# ---------------------------------------------------------------------------
# ProductionRun.is_multi_plate
# ---------------------------------------------------------------------------


class TestProductionRunIsMultiPlate:
    def test_zero_plates_is_not_multi(self):
        obj = make_production_run(total_plates=0)
        assert ProductionRun.is_multi_plate.fget(obj) is False

    def test_one_plate_is_multi(self):
        obj = make_production_run(total_plates=1)
        assert ProductionRun.is_multi_plate.fget(obj) is True

    def test_many_plates_is_multi(self):
        obj = make_production_run(total_plates=5)
        assert ProductionRun.is_multi_plate.fget(obj) is True


# ---------------------------------------------------------------------------
# ProductionRun.plates_progress_percentage
# ---------------------------------------------------------------------------


class TestProductionRunPlatesProgressPercentage:
    def test_zero_total_plates_returns_zero(self):
        obj = make_production_run(total_plates=0, completed_plates=0)
        assert ProductionRun.plates_progress_percentage.fget(obj) == 0.0

    def test_half_complete(self):
        obj = make_production_run(total_plates=4, completed_plates=2)
        assert abs(ProductionRun.plates_progress_percentage.fget(obj) - 50.0) < 0.001

    def test_fully_complete(self):
        obj = make_production_run(total_plates=3, completed_plates=3)
        assert abs(ProductionRun.plates_progress_percentage.fget(obj) - 100.0) < 0.001

    def test_none_complete(self):
        obj = make_production_run(total_plates=5, completed_plates=0)
        assert ProductionRun.plates_progress_percentage.fget(obj) == 0.0


# ---------------------------------------------------------------------------
# ProductionRun.is_all_plates_complete
# ---------------------------------------------------------------------------


class TestProductionRunIsAllPlatesComplete:
    def test_no_plates_is_false(self):
        obj = make_production_run(total_plates=0, completed_plates=0)
        obj.is_multi_plate = False
        assert ProductionRun.is_all_plates_complete.fget(obj) is False

    def test_all_complete_is_true(self):
        obj = make_production_run(total_plates=3, completed_plates=3)
        obj.is_multi_plate = True
        assert ProductionRun.is_all_plates_complete.fget(obj) is True

    def test_partial_complete_is_false(self):
        obj = make_production_run(total_plates=3, completed_plates=2)
        obj.is_multi_plate = True
        assert ProductionRun.is_all_plates_complete.fget(obj) is False


# ---------------------------------------------------------------------------
# ProductionRunMaterial.estimated_total_weight
# ---------------------------------------------------------------------------


class TestProductionRunMaterialEstimatedTotalWeight:
    def test_sums_all_three_components(self):
        obj = make_production_run_material(
            estimated_model_weight_grams=Decimal("100"),
            estimated_flushed_grams=Decimal("10"),
            estimated_tower_grams=Decimal("5"),
        )
        assert ProductionRunMaterial.estimated_total_weight.fget(obj) == Decimal("115")

    def test_with_zero_flush_and_tower(self):
        obj = make_production_run_material(
            estimated_model_weight_grams=Decimal("80"),
            estimated_flushed_grams=Decimal("0"),
            estimated_tower_grams=Decimal("0"),
        )
        assert ProductionRunMaterial.estimated_total_weight.fget(obj) == Decimal("80")

    def test_none_values_treated_as_zero(self):
        obj = make_production_run_material(
            estimated_model_weight_grams=None,
            estimated_flushed_grams=None,
            estimated_tower_grams=None,
        )
        assert ProductionRunMaterial.estimated_total_weight.fget(obj) == Decimal("0")


# ---------------------------------------------------------------------------
# ProductionRunMaterial.actual_weight_from_weighing
# ---------------------------------------------------------------------------


class TestProductionRunMaterialActualWeightFromWeighing:
    def test_both_weights_calculates_difference(self):
        obj = make_production_run_material(
            spool_weight_before_grams=Decimal("300"),
            spool_weight_after_grams=Decimal("200"),
        )
        assert ProductionRunMaterial.actual_weight_from_weighing.fget(obj) == Decimal("100")

    def test_before_none_returns_none(self):
        obj = make_production_run_material(
            spool_weight_before_grams=None,
            spool_weight_after_grams=Decimal("200"),
        )
        assert ProductionRunMaterial.actual_weight_from_weighing.fget(obj) is None

    def test_after_none_returns_none(self):
        obj = make_production_run_material(
            spool_weight_before_grams=Decimal("300"),
            spool_weight_after_grams=None,
        )
        assert ProductionRunMaterial.actual_weight_from_weighing.fget(obj) is None

    def test_both_none_returns_none(self):
        obj = make_production_run_material(
            spool_weight_before_grams=None,
            spool_weight_after_grams=None,
        )
        assert ProductionRunMaterial.actual_weight_from_weighing.fget(obj) is None


# ---------------------------------------------------------------------------
# ProductionRunMaterial.actual_total_weight
# ---------------------------------------------------------------------------


class TestProductionRunMaterialActualTotalWeight:
    def test_uses_weighing_when_available(self):
        obj = make_production_run_material(
            spool_weight_before_grams=Decimal("500"),
            spool_weight_after_grams=Decimal("400"),
            actual_model_weight_grams=Decimal("50"),
            actual_flushed_grams=Decimal("5"),
            actual_tower_grams=Decimal("5"),
        )
        obj.actual_weight_from_weighing = Decimal("100")
        assert ProductionRunMaterial.actual_total_weight.fget(obj) == Decimal("100")

    def test_falls_back_to_manual_entries(self):
        obj = make_production_run_material(
            spool_weight_before_grams=None,
            spool_weight_after_grams=None,
            actual_model_weight_grams=Decimal("80"),
            actual_flushed_grams=Decimal("10"),
            actual_tower_grams=Decimal("5"),
        )
        obj.actual_weight_from_weighing = None
        assert ProductionRunMaterial.actual_total_weight.fget(obj) == Decimal("95")

    def test_all_none_returns_zero(self):
        obj = make_production_run_material(
            spool_weight_before_grams=None,
            spool_weight_after_grams=None,
            actual_model_weight_grams=None,
            actual_flushed_grams=None,
            actual_tower_grams=None,
        )
        obj.actual_weight_from_weighing = None
        assert ProductionRunMaterial.actual_total_weight.fget(obj) == Decimal("0")


# ---------------------------------------------------------------------------
# ProductionRunMaterial.variance_grams and variance_percentage
# ---------------------------------------------------------------------------


class TestProductionRunMaterialVariance:
    def test_variance_grams_positive_overrun(self):
        obj = make_production_run_material()
        obj.actual_total_weight = Decimal("110")
        obj.estimated_total_weight = Decimal("100")
        assert ProductionRunMaterial.variance_grams.fget(obj) == Decimal("10")

    def test_variance_grams_negative_underrun(self):
        obj = make_production_run_material()
        obj.actual_total_weight = Decimal("90")
        obj.estimated_total_weight = Decimal("100")
        assert ProductionRunMaterial.variance_grams.fget(obj) == Decimal("-10")

    def test_variance_percentage_basic(self):
        obj = make_production_run_material()
        obj.variance_grams = Decimal("10")
        obj.estimated_total_weight = Decimal("100")
        result = ProductionRunMaterial.variance_percentage.fget(obj)
        assert abs(result - Decimal("10")) < Decimal("0.01")

    def test_variance_percentage_zero_estimated(self):
        obj = make_production_run_material()
        obj.variance_grams = Decimal("10")
        obj.estimated_total_weight = Decimal("0")
        assert ProductionRunMaterial.variance_percentage.fget(obj) == Decimal("0")


# ---------------------------------------------------------------------------
# ProductionRunMaterial.total_cost
# ---------------------------------------------------------------------------


class TestProductionRunMaterialTotalCost:
    def test_calculates_actual_weight_times_cost_per_gram(self):
        obj = make_production_run_material(cost_per_gram=Decimal("0.02"))
        obj.actual_total_weight = Decimal("100")
        assert ProductionRunMaterial.total_cost.fget(obj) == Decimal("2.00")

    def test_zero_weight_gives_zero_cost(self):
        obj = make_production_run_material(cost_per_gram=Decimal("0.05"))
        obj.actual_total_weight = Decimal("0")
        assert ProductionRunMaterial.total_cost.fget(obj) == Decimal("0.00")


# ---------------------------------------------------------------------------
# ProductionRunPlate.is_complete / is_pending / is_printing
# ---------------------------------------------------------------------------


class TestProductionRunPlateStatus:
    def test_complete_status(self):
        obj = make_plate(status="complete")
        assert ProductionRunPlate.is_complete.fget(obj) is True
        assert ProductionRunPlate.is_pending.fget(obj) is False
        assert ProductionRunPlate.is_printing.fget(obj) is False

    def test_pending_status(self):
        obj = make_plate(status="pending")
        assert ProductionRunPlate.is_pending.fget(obj) is True
        assert ProductionRunPlate.is_complete.fget(obj) is False
        assert ProductionRunPlate.is_printing.fget(obj) is False

    def test_printing_status(self):
        obj = make_plate(status="printing")
        assert ProductionRunPlate.is_printing.fget(obj) is True
        assert ProductionRunPlate.is_complete.fget(obj) is False
        assert ProductionRunPlate.is_pending.fget(obj) is False

    def test_failed_is_none_of_the_three(self):
        obj = make_plate(status="failed")
        assert ProductionRunPlate.is_complete.fget(obj) is False
        assert ProductionRunPlate.is_pending.fget(obj) is False
        assert ProductionRunPlate.is_printing.fget(obj) is False


# ---------------------------------------------------------------------------
# ProductionRunPlate.total_items_expected
# ---------------------------------------------------------------------------


class TestProductionRunPlateTotalItemsExpected:
    def test_basic_calculation(self):
        obj = make_plate(quantity=3, prints_per_plate=4)
        assert ProductionRunPlate.total_items_expected.fget(obj) == 12

    def test_single_print(self):
        obj = make_plate(quantity=1, prints_per_plate=1)
        assert ProductionRunPlate.total_items_expected.fget(obj) == 1

    def test_zero_quantity(self):
        obj = make_plate(quantity=0, prints_per_plate=4)
        assert ProductionRunPlate.total_items_expected.fget(obj) == 0


# ---------------------------------------------------------------------------
# ProductionRunPlate.total_items_completed
# ---------------------------------------------------------------------------


class TestProductionRunPlateTotalItemsCompleted:
    def test_returns_successful_prints(self):
        obj = make_plate(successful_prints=7)
        assert ProductionRunPlate.total_items_completed.fget(obj) == 7

    def test_zero_completed(self):
        obj = make_plate(successful_prints=0)
        assert ProductionRunPlate.total_items_completed.fget(obj) == 0


# ---------------------------------------------------------------------------
# ProductionRunPlate.progress_percentage
# ---------------------------------------------------------------------------


class TestProductionRunPlateProgressPercentage:
    def test_zero_expected_returns_zero(self):
        obj = make_plate(quantity=0, prints_per_plate=1, successful_prints=0)
        obj.total_items_expected = 0
        assert ProductionRunPlate.progress_percentage.fget(obj) == 0.0

    def test_half_complete(self):
        obj = make_plate(quantity=1, prints_per_plate=4, successful_prints=2)
        obj.total_items_expected = 4
        assert abs(ProductionRunPlate.progress_percentage.fget(obj) - 50.0) < 0.001

    def test_fully_complete(self):
        obj = make_plate(quantity=2, prints_per_plate=3, successful_prints=6)
        obj.total_items_expected = 6
        assert abs(ProductionRunPlate.progress_percentage.fget(obj) - 100.0) < 0.001


# ---------------------------------------------------------------------------
# ProductionRunPlate.total_estimated_time_minutes
# ---------------------------------------------------------------------------


class TestProductionRunPlateTotalEstimatedTimeMinutes:
    def test_calculates_correctly(self):
        obj = make_plate(print_time_minutes=90, quantity=3)
        assert ProductionRunPlate.total_estimated_time_minutes.fget(obj) == 270

    def test_no_print_time_returns_none(self):
        obj = make_plate(print_time_minutes=None, quantity=3)
        assert ProductionRunPlate.total_estimated_time_minutes.fget(obj) is None

    def test_no_quantity_returns_none(self):
        obj = make_plate(print_time_minutes=90, quantity=None)
        assert ProductionRunPlate.total_estimated_time_minutes.fget(obj) is None


# ---------------------------------------------------------------------------
# ProductionRunPlate.total_estimated_material_grams
# ---------------------------------------------------------------------------


class TestProductionRunPlateTotalEstimatedMaterialGrams:
    def test_calculates_correctly(self):
        obj = make_plate(estimated_material_weight_grams=Decimal("50"), quantity=3)
        assert ProductionRunPlate.total_estimated_material_grams.fget(obj) == Decimal("150")

    def test_no_material_weight_returns_none(self):
        obj = make_plate(estimated_material_weight_grams=None, quantity=3)
        assert ProductionRunPlate.total_estimated_material_grams.fget(obj) is None


# ---------------------------------------------------------------------------
# InventoryTransaction.is_deduction and is_addition
# ---------------------------------------------------------------------------


class TestInventoryTransactionDirection:
    def test_negative_weight_is_deduction(self):
        obj = make_inventory_transaction(weight_change=Decimal("-50"))
        assert InventoryTransaction.is_deduction.fget(obj) is True
        assert InventoryTransaction.is_addition.fget(obj) is False

    def test_positive_weight_is_addition(self):
        obj = make_inventory_transaction(weight_change=Decimal("100"))
        assert InventoryTransaction.is_addition.fget(obj) is True
        assert InventoryTransaction.is_deduction.fget(obj) is False

    def test_zero_weight_is_neither(self):
        obj = make_inventory_transaction(weight_change=Decimal("0"))
        assert InventoryTransaction.is_deduction.fget(obj) is False
        assert InventoryTransaction.is_addition.fget(obj) is False


# ---------------------------------------------------------------------------
# AMSSlotMapping.absolute_slot_id
# ---------------------------------------------------------------------------


class TestAMSSlotMappingAbsoluteSlotId:
    def test_first_ams_first_tray(self):
        obj = make_ams_slot(ams_id=0, tray_id=0)
        assert AMSSlotMapping.absolute_slot_id.fget(obj) == 0

    def test_first_ams_fourth_tray(self):
        obj = make_ams_slot(ams_id=0, tray_id=3)
        assert AMSSlotMapping.absolute_slot_id.fget(obj) == 3

    def test_second_ams_first_tray(self):
        obj = make_ams_slot(ams_id=1, tray_id=0)
        assert AMSSlotMapping.absolute_slot_id.fget(obj) == 4

    def test_second_ams_third_tray(self):
        obj = make_ams_slot(ams_id=1, tray_id=2)
        assert AMSSlotMapping.absolute_slot_id.fget(obj) == 6


# ---------------------------------------------------------------------------
# AMSSlotMapping.slot_display_name
# ---------------------------------------------------------------------------


class TestAMSSlotMappingSlotDisplayName:
    def test_first_ams_first_slot(self):
        obj = make_ams_slot(ams_id=0, tray_id=0)
        assert AMSSlotMapping.slot_display_name.fget(obj) == "AMS 1 Slot 1"

    def test_second_ams_fourth_slot(self):
        obj = make_ams_slot(ams_id=1, tray_id=3)
        assert AMSSlotMapping.slot_display_name.fget(obj) == "AMS 2 Slot 4"

    def test_third_ams_second_slot(self):
        obj = make_ams_slot(ams_id=2, tray_id=1)
        assert AMSSlotMapping.slot_display_name.fget(obj) == "AMS 3 Slot 2"


# ---------------------------------------------------------------------------
# AMSSlotMapping.color_hex_normalized
# ---------------------------------------------------------------------------


class TestAMSSlotMappingColorHexNormalized:
    def test_none_color_returns_none(self):
        obj = make_ams_slot(last_reported_color=None)
        assert AMSSlotMapping.color_hex_normalized.fget(obj) is None

    def test_six_char_color_returned_as_is(self):
        obj = make_ams_slot(last_reported_color="FF5733")
        assert AMSSlotMapping.color_hex_normalized.fget(obj) == "FF5733"

    def test_eight_char_rgba_strips_alpha(self):
        obj = make_ams_slot(last_reported_color="FF5733FF")
        assert AMSSlotMapping.color_hex_normalized.fget(obj) == "FF5733"

    def test_short_color_returns_none(self):
        obj = make_ams_slot(last_reported_color="FF57")
        assert AMSSlotMapping.color_hex_normalized.fget(obj) is None


# ---------------------------------------------------------------------------
# Printer.bed_size_str
# ---------------------------------------------------------------------------


class TestPrinterBedSizeStr:
    def test_all_dimensions_set(self):
        obj = make_printer(bed_size_x_mm=256, bed_size_y_mm=256, bed_size_z_mm=256)
        assert Printer.bed_size_str.fget(obj) == "256x256x256"

    def test_asymmetric_dimensions(self):
        obj = make_printer(bed_size_x_mm=180, bed_size_y_mm=180, bed_size_z_mm=180)
        assert Printer.bed_size_str.fget(obj) == "180x180x180"

    def test_any_dimension_none_returns_none(self):
        obj = make_printer(bed_size_x_mm=256, bed_size_y_mm=None, bed_size_z_mm=256)
        assert Printer.bed_size_str.fget(obj) is None

    def test_all_none_returns_none(self):
        obj = make_printer()
        assert Printer.bed_size_str.fget(obj) is None
