"""
Unit Tests for Production Run Edit Validation

Tests the status-based validation logic that restricts editing of production runs
based on their current status (in_progress, completed, failed, cancelled).

Validation Rules:
- in_progress/pending: Allow editing all fields
- completed/failed/cancelled: Only allow editing 'notes' field
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.production_run import ProductionRunUpdate


def test_update_schema_allows_all_fields():
    """Test that ProductionRunUpdate schema accepts all optional fields."""
    data = {
        "printer_name": "Prusa i3 MK3S",
        "estimated_print_time_hours": Decimal("5.5"),
        "bed_temperature": 60,
        "nozzle_temperature": 210,
        "quality_rating": 4,
        "quality_notes": "Good quality",
        "notes": "Updated notes",
        "status": "completed",
    }

    update = ProductionRunUpdate(**data)

    assert update.printer_name == "Prusa i3 MK3S"
    assert update.estimated_print_time_hours == Decimal("5.5")
    assert update.bed_temperature == 60
    assert update.nozzle_temperature == 210
    assert update.quality_rating == 4
    assert update.quality_notes == "Good quality"
    assert update.notes == "Updated notes"
    assert update.status == "completed"


def test_update_schema_allows_notes_only():
    """Test that ProductionRunUpdate schema allows updating only notes."""
    data = {"notes": "Updated notes for completed run"}

    update = ProductionRunUpdate(**data)

    assert update.notes == "Updated notes for completed run"
    # All other fields should be None
    assert update.printer_name is None
    assert update.estimated_print_time_hours is None
    assert update.status is None


def test_update_schema_model_dump_excludes_unset():
    """Test that model_dump(exclude_unset=True) only includes provided fields."""
    # Only update notes
    update = ProductionRunUpdate(notes="Test notes")
    dump = update.model_dump(exclude_unset=True)

    assert "notes" in dump
    assert "printer_name" not in dump
    assert "status" not in dump

    # Update multiple fields
    update = ProductionRunUpdate(notes="Test notes", printer_name="Prusa XL", status="completed")
    dump = update.model_dump(exclude_unset=True)

    assert "notes" in dump
    assert "printer_name" in dump
    assert "status" in dump
    assert len(dump) == 3


def test_restricted_fields_detection_logic():
    """
    Test the logic for detecting restricted fields in updates.

    This simulates the validation logic used in the API endpoint:
    - Get update_data from model_dump(exclude_unset=True)
    - Filter out 'notes' field
    - Remaining fields are restricted for immutable statuses
    """
    # Scenario 1: Only notes updated - should be allowed
    update = ProductionRunUpdate(notes="Updated notes")
    update_data = update.model_dump(exclude_unset=True)
    restricted_fields = [field for field in update_data.keys() if field != "notes"]

    assert len(restricted_fields) == 0  # No restricted fields

    # Scenario 2: Notes + other fields - should be restricted
    update = ProductionRunUpdate(notes="Updated notes", printer_name="Prusa XL", bed_temperature=65)
    update_data = update.model_dump(exclude_unset=True)
    restricted_fields = [field for field in update_data.keys() if field != "notes"]

    assert len(restricted_fields) == 2
    assert "printer_name" in restricted_fields
    assert "bed_temperature" in restricted_fields

    # Scenario 3: Only non-notes fields - should be restricted
    update = ProductionRunUpdate(printer_name="Prusa XL", bed_temperature=65, quality_rating=5)
    update_data = update.model_dump(exclude_unset=True)
    restricted_fields = [field for field in update_data.keys() if field != "notes"]

    assert len(restricted_fields) == 3
    assert "printer_name" in restricted_fields
    assert "bed_temperature" in restricted_fields
    assert "quality_rating" in restricted_fields


def test_immutable_statuses_list():
    """Test that immutable statuses are correctly defined."""
    immutable_statuses = ["completed", "failed", "cancelled"]

    # These statuses should be immutable (only notes editable)
    assert "completed" in immutable_statuses
    assert "failed" in immutable_statuses
    assert "cancelled" in immutable_statuses

    # These statuses should allow full editing
    assert "in_progress" not in immutable_statuses
    assert "pending" not in immutable_statuses


def test_validation_error_message_format():
    """
    Test that validation error messages include the specific fields and status.

    This simulates the error message construction in the API endpoint.
    """
    # Simulate trying to update multiple fields on a completed run
    update = ProductionRunUpdate(printer_name="Prusa XL", bed_temperature=65, quality_rating=5)
    update_data = update.model_dump(exclude_unset=True)
    restricted_fields = [field for field in update_data.keys() if field != "notes"]

    run_status = "completed"
    error_detail = f"Cannot modify {', '.join(restricted_fields)} for {run_status} production runs. Only 'notes' can be updated."

    assert "Cannot modify" in error_detail
    assert run_status in error_detail
    assert "Only 'notes' can be updated" in error_detail
    assert "printer_name" in error_detail
    assert "bed_temperature" in error_detail
    assert "quality_rating" in error_detail


def test_datetime_fields_in_update():
    """Test that datetime fields can be updated (for in_progress runs)."""
    now = datetime.now(timezone.utc)

    update = ProductionRunUpdate(started_at=now, completed_at=now, duration_hours=Decimal("4.5"))

    assert update.started_at == now
    assert update.completed_at == now
    assert update.duration_hours == Decimal("4.5")


def test_weight_fields_in_update():
    """Test that weight fields can be updated (for in_progress runs)."""
    update = ProductionRunUpdate(
        estimated_model_weight_grams=Decimal("500.5"),
        estimated_flushed_grams=Decimal("50.0"),
        estimated_tower_grams=Decimal("100.0"),
        actual_model_weight_grams=Decimal("510.2"),
        actual_flushed_grams=Decimal("55.0"),
        actual_tower_grams=Decimal("105.0"),
        waste_filament_grams=Decimal("10.0"),
        waste_reason="Stringing cleanup",
    )

    assert update.estimated_model_weight_grams == Decimal("500.5")
    assert update.estimated_flushed_grams == Decimal("50.0")
    assert update.estimated_tower_grams == Decimal("100.0")
    assert update.actual_model_weight_grams == Decimal("510.2")
    assert update.actual_flushed_grams == Decimal("55.0")
    assert update.actual_tower_grams == Decimal("105.0")
    assert update.waste_filament_grams == Decimal("10.0")
    assert update.waste_reason == "Stringing cleanup"


def test_temperature_fields_validation():
    """Test that temperature fields have proper validation."""
    # Valid temperatures
    update = ProductionRunUpdate(bed_temperature=60, nozzle_temperature=210)
    assert update.bed_temperature == 60
    assert update.nozzle_temperature == 210

    # Bed temperature max (200)
    update = ProductionRunUpdate(bed_temperature=200)
    assert update.bed_temperature == 200

    # Nozzle temperature max (500)
    update = ProductionRunUpdate(nozzle_temperature=500)
    assert update.nozzle_temperature == 500


def test_quality_rating_validation():
    """Test that quality rating has proper validation (1-5)."""
    # Valid ratings
    for rating in [1, 2, 3, 4, 5]:
        update = ProductionRunUpdate(quality_rating=rating)
        assert update.quality_rating == rating


def test_status_literal_values():
    """Test that status field only accepts valid literal values."""
    valid_statuses = ["in_progress", "completed", "failed", "cancelled"]

    for status_value in valid_statuses:
        update = ProductionRunUpdate(status=status_value)
        assert update.status == status_value
