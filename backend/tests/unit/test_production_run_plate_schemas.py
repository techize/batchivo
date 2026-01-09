"""Unit tests for ProductionRunPlate Pydantic schemas."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.production_run_plate import (
    ProductionRunPlateBase,
    ProductionRunPlateCreate,
    ProductionRunPlateUpdate,
    ProductionRunPlateResponse,
    ProductionRunPlateSummary,
    ProductionRunPlateListResponse,
    MarkPlateCompleteRequest,
)
from app.schemas.printer import PrinterSummary
from app.schemas.production_run import ModelSummary


class TestProductionRunPlateBase:
    """Tests for ProductionRunPlateBase schema."""

    def test_plate_base_valid_minimal(self):
        """Test creating plate with required fields only."""
        data = {
            "plate_number": 1,
            "plate_name": "Dragon Bodies",
            "prints_per_plate": 3,
        }
        plate = ProductionRunPlateBase(**data)
        assert plate.plate_number == 1
        assert plate.plate_name == "Dragon Bodies"
        assert plate.quantity == 1  # Default
        assert plate.prints_per_plate == 3

    def test_plate_base_valid_full(self):
        """Test creating plate with all fields."""
        data = {
            "plate_number": 2,
            "plate_name": "Dragon Tongues (A1 Mini)",
            "quantity": 5,
            "prints_per_plate": 6,
            "print_time_minutes": 45,
            "estimated_material_weight_grams": Decimal("30.5"),
            "notes": "Multi-color plate",
        }
        plate = ProductionRunPlateBase(**data)
        assert plate.plate_number == 2
        assert plate.plate_name == "Dragon Tongues (A1 Mini)"
        assert plate.quantity == 5
        assert plate.prints_per_plate == 6
        assert plate.print_time_minutes == 45
        assert plate.estimated_material_weight_grams == Decimal("30.5")
        assert plate.notes == "Multi-color plate"

    def test_plate_base_plate_number_zero_fails(self):
        """Test that plate_number < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateBase(
                plate_number=0,
                plate_name="Test",
                prints_per_plate=1,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_plate_base_negative_plate_number_fails(self):
        """Test that negative plate_number raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateBase(
                plate_number=-1,
                plate_name="Test",
                prints_per_plate=1,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_plate_base_empty_plate_name_fails(self):
        """Test that empty plate_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateBase(
                plate_number=1,
                plate_name="",
                prints_per_plate=1,
            )
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_plate_base_plate_name_too_long_fails(self):
        """Test that plate_name > 200 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateBase(
                plate_number=1,
                plate_name="A" * 201,
                prints_per_plate=1,
            )
        assert "String should have at most 200 characters" in str(exc_info.value)

    def test_plate_base_quantity_zero_fails(self):
        """Test that quantity < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateBase(
                plate_number=1,
                plate_name="Test",
                quantity=0,
                prints_per_plate=1,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_plate_base_prints_per_plate_zero_fails(self):
        """Test that prints_per_plate < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateBase(
                plate_number=1,
                plate_name="Test",
                prints_per_plate=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_plate_base_invalid_print_time_fails(self):
        """Test that print_time_minutes < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateBase(
                plate_number=1,
                plate_name="Test",
                prints_per_plate=1,
                print_time_minutes=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_plate_base_invalid_material_weight_fails(self):
        """Test that estimated_material_weight_grams < 0.01 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateBase(
                plate_number=1,
                plate_name="Test",
                prints_per_plate=1,
                estimated_material_weight_grams=Decimal("0.001"),
            )
        assert "greater than or equal to 0.01" in str(exc_info.value)


class TestProductionRunPlateCreate:
    """Tests for ProductionRunPlateCreate schema."""

    def test_plate_create_valid(self):
        """Test creating a valid plate."""
        model_id = uuid4()
        printer_id = uuid4()
        data = {
            "model_id": model_id,
            "printer_id": printer_id,
            "plate_number": 1,
            "plate_name": "Dragon Bodies",
            "quantity": 2,
            "prints_per_plate": 3,
        }
        plate = ProductionRunPlateCreate(**data)
        assert plate.model_id == model_id
        assert plate.printer_id == printer_id
        assert plate.status == "pending"  # Default

    def test_plate_create_with_status(self):
        """Test creating plate with specific status."""
        data = {
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Dragon Bodies",
            "prints_per_plate": 3,
            "status": "printing",
        }
        plate = ProductionRunPlateCreate(**data)
        assert plate.status == "printing"

    def test_plate_create_requires_model_id(self):
        """Test that model_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateCreate(
                printer_id=uuid4(),
                plate_number=1,
                plate_name="Test",
                prints_per_plate=1,
            )
        assert "model_id" in str(exc_info.value)

    def test_plate_create_requires_printer_id(self):
        """Test that printer_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateCreate(
                model_id=uuid4(),
                plate_number=1,
                plate_name="Test",
                prints_per_plate=1,
            )
        assert "printer_id" in str(exc_info.value)

    def test_plate_create_invalid_status_fails(self):
        """Test that invalid status raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateCreate(
                model_id=uuid4(),
                printer_id=uuid4(),
                plate_number=1,
                plate_name="Test",
                prints_per_plate=1,
                status="invalid",
            )
        assert "Input should be" in str(exc_info.value)


class TestProductionRunPlateUpdate:
    """Tests for ProductionRunPlateUpdate schema."""

    def test_plate_update_all_optional(self):
        """Test that all fields are optional for update."""
        update = ProductionRunPlateUpdate()
        assert update.status is None
        assert update.started_at is None
        assert update.successful_prints is None

    def test_plate_update_partial(self):
        """Test partial update with only some fields."""
        now = datetime.now()
        data = {
            "status": "printing",
            "started_at": now,
        }
        update = ProductionRunPlateUpdate(**data)
        assert update.status == "printing"
        assert update.started_at == now
        assert update.completed_at is None

    def test_plate_update_completion(self):
        """Test updating plate with completion data."""
        now = datetime.now()
        data = {
            "status": "complete",
            "completed_at": now,
            "actual_print_time_minutes": 47,
            "actual_material_weight_grams": Decimal("32.5"),
            "successful_prints": 3,
            "failed_prints": 0,
        }
        update = ProductionRunPlateUpdate(**data)
        assert update.status == "complete"
        assert update.actual_print_time_minutes == 47
        assert update.successful_prints == 3

    def test_plate_update_valid_statuses(self):
        """Test all valid status values."""
        valid_statuses = ["pending", "printing", "complete", "failed", "cancelled"]
        for status in valid_statuses:
            update = ProductionRunPlateUpdate(status=status)
            assert update.status == status

    def test_plate_update_negative_successful_prints_fails(self):
        """Test that negative successful_prints raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateUpdate(successful_prints=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_plate_update_negative_failed_prints_fails(self):
        """Test that negative failed_prints raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunPlateUpdate(failed_prints=-1)
        assert "greater than or equal to 0" in str(exc_info.value)


class TestProductionRunPlateResponse:
    """Tests for ProductionRunPlateResponse schema."""

    def test_plate_response_valid(self):
        """Test creating a valid plate response."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Dragon Bodies",
            "quantity": 2,
            "prints_per_plate": 3,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.plate_number == 1
        assert response.status == "pending"
        assert response.successful_prints == 0  # Default

    def test_plate_response_is_complete_computed(self):
        """Test is_complete computed field."""
        now = datetime.now()
        base_data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 1,
            "prints_per_plate": 3,
            "created_at": now,
            "updated_at": now,
        }

        # Complete status
        data_complete = {**base_data, "status": "complete"}
        response_complete = ProductionRunPlateResponse(**data_complete)
        assert response_complete.is_complete is True

        # Pending status
        data_pending = {**base_data, "status": "pending"}
        response_pending = ProductionRunPlateResponse(**data_pending)
        assert response_pending.is_complete is False

    def test_plate_response_is_pending_computed(self):
        """Test is_pending computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 1,
            "prints_per_plate": 3,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.is_pending is True
        assert response.is_printing is False

    def test_plate_response_is_printing_computed(self):
        """Test is_printing computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 1,
            "prints_per_plate": 3,
            "status": "printing",
            "created_at": now,
            "updated_at": now,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.is_printing is True
        assert response.is_pending is False

    def test_plate_response_total_items_expected_computed(self):
        """Test total_items_expected computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 2,  # 2 plates
            "prints_per_plate": 3,  # 3 per plate = 6 total
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.total_items_expected == 6

    def test_plate_response_progress_percentage_computed(self):
        """Test progress_percentage computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 2,
            "prints_per_plate": 5,  # 10 expected
            "status": "printing",
            "successful_prints": 7,  # 70% complete
            "created_at": now,
            "updated_at": now,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.progress_percentage == 70.0

    def test_plate_response_progress_percentage_zero_when_no_expected(self):
        """Test progress_percentage is 0 when total_items_expected is 0."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 0,  # Edge case (should be validated elsewhere)
            "prints_per_plate": 3,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        # Note: quantity=0 would normally fail validation, but we test the computed field logic
        response = ProductionRunPlateResponse.model_construct(**data)
        assert response.progress_percentage == 0.0

    def test_plate_response_total_estimated_time_computed(self):
        """Test total_estimated_time_minutes computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 3,  # 3 plates
            "prints_per_plate": 5,
            "print_time_minutes": 45,  # 45 × 3 = 135
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.total_estimated_time_minutes == 135

    def test_plate_response_total_estimated_time_none_when_no_time(self):
        """Test total_estimated_time is None when print_time is None."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 3,
            "prints_per_plate": 5,
            "print_time_minutes": None,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.total_estimated_time_minutes is None

    def test_plate_response_total_estimated_material_computed(self):
        """Test total_estimated_material_grams computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 4,  # 4 plates
            "prints_per_plate": 5,
            "estimated_material_weight_grams": Decimal("30.5"),  # 30.5 × 4 = 122.0
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.total_estimated_material_grams == 122.0

    def test_plate_response_with_nested_model_and_printer(self):
        """Test plate response with nested model and printer summaries."""
        now = datetime.now()
        model_summary = ModelSummary(id=uuid4(), sku="DRG-001", name="Dragon Body")
        printer_summary = PrinterSummary(id=uuid4(), name="Bambu A1 Mini")

        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": model_summary.id,
            "printer_id": printer_summary.id,
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 1,
            "prints_per_plate": 3,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
            "model": model_summary,
            "printer": printer_summary,
        }
        response = ProductionRunPlateResponse(**data)
        assert response.model.name == "Dragon Body"
        assert response.printer.name == "Bambu A1 Mini"

    def test_plate_response_from_attributes(self):
        """Test that from_attributes is enabled for ORM conversion."""
        assert ProductionRunPlateResponse.model_config.get("from_attributes") is True


class TestProductionRunPlateSummary:
    """Tests for ProductionRunPlateSummary schema."""

    def test_plate_summary_valid(self):
        """Test creating a valid plate summary."""
        data = {
            "id": uuid4(),
            "plate_number": 1,
            "plate_name": "Dragon Bodies",
            "status": "pending",
            "quantity": 2,
            "prints_per_plate": 3,
            "successful_prints": 4,
            "failed_prints": 0,
        }
        summary = ProductionRunPlateSummary(**data)
        assert summary.plate_number == 1
        assert summary.status == "pending"
        assert summary.total_items_expected == 6
        assert summary.progress_percentage == pytest.approx(66.67, rel=0.01)

    def test_plate_summary_minimal(self):
        """Test plate summary with defaults."""
        data = {
            "id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "status": "pending",
            "quantity": 1,
            "prints_per_plate": 1,
        }
        summary = ProductionRunPlateSummary(**data)
        assert summary.successful_prints == 0  # Default
        assert summary.failed_prints == 0  # Default


class TestProductionRunPlateListResponse:
    """Tests for ProductionRunPlateListResponse schema."""

    def test_plate_list_response_valid(self):
        """Test creating a valid list response."""
        now = datetime.now()
        plate_data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Test",
            "quantity": 1,
            "prints_per_plate": 3,
            "status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        data = {
            "plates": [ProductionRunPlateResponse(**plate_data)],
            "total": 1,
            "skip": 0,
            "limit": 10,
        }
        response = ProductionRunPlateListResponse(**data)
        assert len(response.plates) == 1
        assert response.total == 1

    def test_plate_list_response_empty(self):
        """Test list response with empty list."""
        data = {
            "plates": [],
            "total": 0,
            "skip": 0,
            "limit": 10,
        }
        response = ProductionRunPlateListResponse(**data)
        assert len(response.plates) == 0


class TestMarkPlateCompleteRequest:
    """Tests for MarkPlateCompleteRequest schema."""

    def test_mark_complete_valid(self):
        """Test creating a valid mark complete request."""
        data = {
            "successful_prints": 3,
            "failed_prints": 0,
            "actual_print_time_minutes": 47,
            "actual_material_weight_grams": Decimal("32.5"),
            "notes": "Clean print, no issues",
        }
        request = MarkPlateCompleteRequest(**data)
        assert request.successful_prints == 3
        assert request.failed_prints == 0

    def test_mark_complete_minimal(self):
        """Test mark complete with only required field."""
        request = MarkPlateCompleteRequest(successful_prints=3)
        assert request.successful_prints == 3
        assert request.failed_prints == 0  # Default
        assert request.actual_print_time_minutes is None
        assert request.notes is None

    def test_mark_complete_requires_successful_prints(self):
        """Test that successful_prints is required."""
        with pytest.raises(ValidationError) as exc_info:
            MarkPlateCompleteRequest()
        assert "successful_prints" in str(exc_info.value)

    def test_mark_complete_negative_successful_prints_fails(self):
        """Test that negative successful_prints raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MarkPlateCompleteRequest(successful_prints=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_mark_complete_negative_failed_prints_fails(self):
        """Test that negative failed_prints raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MarkPlateCompleteRequest(successful_prints=3, failed_prints=-1)
        assert "greater than or equal to 0" in str(exc_info.value)


class TestProductionRunPlateEdgeCases:
    """Edge case tests for ProductionRunPlate schemas."""

    def test_high_quantity_and_prints_per_plate(self):
        """Test with high quantity and prints per plate values."""
        data = {
            "plate_number": 100,
            "plate_name": "Mass Production Plate",
            "quantity": 50,
            "prints_per_plate": 20,  # 1000 total items
        }
        plate = ProductionRunPlateBase(**data)
        assert plate.quantity == 50
        assert plate.prints_per_plate == 20

    def test_all_valid_status_values(self):
        """Test all valid plate status values."""
        now = datetime.now()
        valid_statuses = ["pending", "printing", "complete", "failed", "cancelled"]
        for status in valid_statuses:
            data = {
                "id": uuid4(),
                "production_run_id": uuid4(),
                "model_id": uuid4(),
                "printer_id": uuid4(),
                "plate_number": 1,
                "plate_name": "Test",
                "quantity": 1,
                "prints_per_plate": 1,
                "status": status,
                "created_at": now,
                "updated_at": now,
            }
            response = ProductionRunPlateResponse(**data)
            assert response.status == status

    def test_decimal_material_weight_precision(self):
        """Test decimal precision for material weight."""
        data = {
            "plate_number": 1,
            "plate_name": "Test",
            "prints_per_plate": 1,
            "estimated_material_weight_grams": Decimal("30.125"),
        }
        plate = ProductionRunPlateBase(**data)
        assert plate.estimated_material_weight_grams == Decimal("30.125")

    def test_long_plate_name(self):
        """Test plate name at max length."""
        data = {
            "plate_number": 1,
            "plate_name": "A" * 200,  # Max length
            "prints_per_plate": 1,
        }
        plate = ProductionRunPlateBase(**data)
        assert len(plate.plate_name) == 200

    def test_full_plate_lifecycle(self):
        """Test a plate going through full lifecycle with updates."""
        now = datetime.now()
        base_data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "printer_id": uuid4(),
            "plate_number": 1,
            "plate_name": "Dragon Bodies",
            "quantity": 2,
            "prints_per_plate": 3,
            "print_time_minutes": 45,
            "estimated_material_weight_grams": Decimal("30.0"),
            "created_at": now,
            "updated_at": now,
        }

        # Initial pending state
        pending_data = {**base_data, "status": "pending"}
        pending = ProductionRunPlateResponse(**pending_data)
        assert pending.is_pending is True
        assert pending.progress_percentage == 0.0

        # Start printing
        printing_data = {
            **base_data,
            "status": "printing",
            "started_at": now,
        }
        printing = ProductionRunPlateResponse(**printing_data)
        assert printing.is_printing is True

        # Complete
        complete_data = {
            **base_data,
            "status": "complete",
            "started_at": now,
            "completed_at": now + timedelta(hours=2),
            "actual_print_time_minutes": 93,
            "actual_material_weight_grams": Decimal("62.5"),
            "successful_prints": 6,
            "failed_prints": 0,
        }
        complete = ProductionRunPlateResponse(**complete_data)
        assert complete.is_complete is True
        assert complete.progress_percentage == 100.0
