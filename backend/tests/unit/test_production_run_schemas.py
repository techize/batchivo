"""Unit tests for Production Run Pydantic schemas."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.production_run import (
    ProductionRunCreate,
    ProductionRunUpdate,
    ProductionRunResponse,
    ProductionRunDetailResponse,
    ProductionRunItemCreate,
    ProductionRunItemResponse,
    ProductionRunMaterialCreate,
    ProductionRunMaterialResponse,
)


class TestProductionRunSchemas:
    """Tests for Production Run schemas."""

    def test_production_run_create_valid(self):
        """Test creating a valid production run."""
        data = {
            "started_at": datetime.now(),
            "printer_name": "Prusa i3 MK3S",
            "slicer_software": "PrusaSlicer",
            "status": "in_progress",
        }
        run = ProductionRunCreate(**data)
        assert run.status == "in_progress"
        assert run.printer_name == "Prusa i3 MK3S"
        assert run.is_reprint is False

    def test_production_run_create_invalid_status(self):
        """Test that invalid status raises ValidationError."""
        data = {
            "started_at": datetime.now(),
            "status": "invalid_status",
        }
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunCreate(**data)
        # Literal types provide validation - check error mentions valid options
        error_str = str(exc_info.value)
        assert "in_progress" in error_str or "Input should be" in error_str

    def test_production_run_create_invalid_quality_rating(self):
        """Test that quality rating outside 1-5 raises ValidationError."""
        data = {
            "started_at": datetime.now(),
            "status": "completed",
            "quality_rating": 6,  # Invalid
        }
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunCreate(**data)
        assert "less than or equal to 5" in str(exc_info.value)

    def test_production_run_create_completed_before_started(self):
        """Test that completed_at before started_at raises ValidationError."""
        now = datetime.now()
        data = {
            "started_at": now,
            "completed_at": now - timedelta(hours=1),  # Before started
            "status": "completed",
        }
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunCreate(**data)
        assert "completed_at must be after started_at" in str(exc_info.value)

    def test_production_run_update_partial(self):
        """Test partial updates with optional fields."""
        data = {
            "status": "completed",
            "quality_rating": 5,
            "actual_total_weight_grams": Decimal("250.5"),
        }
        update = ProductionRunUpdate(**data)
        assert update.status == "completed"
        assert update.quality_rating == 5
        assert update.actual_total_weight_grams == Decimal("250.5")
        assert update.printer_name is None  # Not provided

    def test_production_run_response_computed_variance(self):
        """Test variance computed fields in ProductionRunResponse."""
        data = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "run_number": "TEST-20251113-001",
            "started_at": datetime.now(),
            "status": "completed",
            "estimated_total_weight_grams": Decimal("200.0"),
            "estimated_tower_grams": Decimal("20.0"),
            "actual_total_weight_grams": Decimal("230.0"),
            "actual_tower_grams": Decimal("25.0"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = ProductionRunResponse(**data)

        # Variance: actual_total - estimated_total = 230 - 200 = 30g
        assert abs(response.variance_grams - 30.0) < 0.01

        # Variance %: (30 / 200) * 100 = 15.0%
        assert abs(response.variance_percentage - 15.0) < 0.01

    def test_production_run_response_time_variance(self):
        """Test time variance computed fields."""
        data = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "run_number": "TEST-20251113-002",
            "started_at": datetime.now(),
            "status": "completed",
            "estimated_print_time_hours": Decimal("4.0"),
            "duration_hours": Decimal("4.5"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = ProductionRunResponse(**data)

        # Time variance: 4.5 - 4.0 = 0.5 hours
        assert abs(response.time_variance_hours - 0.5) < 0.01

        # Time variance %: (0.5 / 4.0) * 100 = 12.5%
        assert abs(response.time_variance_percentage - 12.5) < 0.01


class TestProductionRunItemSchemas:
    """Tests for Production Run Item schemas."""

    def test_production_run_item_create_valid(self):
        """Test creating a valid production run item."""
        data = {
            "model_id": uuid4(),
            "quantity": 10,
            "bed_position": "front-left",
            "estimated_material_cost": Decimal("5.50"),
            "estimated_total_cost": Decimal("7.25"),
        }
        item = ProductionRunItemCreate(**data)
        assert item.quantity == 10
        assert item.bed_position == "front-left"

    def test_production_run_item_create_invalid_quantity(self):
        """Test that zero or negative quantity raises ValidationError."""
        data = {
            "model_id": uuid4(),
            "quantity": 0,  # Invalid
        }
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunItemCreate(**data)
        assert "greater than 0" in str(exc_info.value)

    def test_production_run_item_response_computed_fields(self):
        """Test computed fields in ProductionRunItemResponse."""
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "quantity": 10,
            "successful_quantity": 8,
            "failed_quantity": 2,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        item = ProductionRunItemResponse(**data)

        # Success rate: (8 / 10) * 100 = 80%
        assert abs(item.success_rate - 80.0) < 0.01

        # Total accounted: 8 + 2 = 10
        assert item.total_quantity_accounted == 10

        # Unaccounted: 10 - 10 = 0
        assert item.unaccounted_quantity == 0

    def test_production_run_item_response_partial_completion(self):
        """Test computed fields with partial completion."""
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "model_id": uuid4(),
            "quantity": 10,
            "successful_quantity": 7,
            "failed_quantity": 1,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        item = ProductionRunItemResponse(**data)

        # Success rate: (7 / 10) * 100 = 70%
        assert abs(item.success_rate - 70.0) < 0.01

        # Unaccounted: 10 - (7 + 1) = 2
        assert item.unaccounted_quantity == 2


class TestProductionRunMaterialSchemas:
    """Tests for Production Run Material schemas."""

    def test_production_run_material_create_valid(self):
        """Test creating a valid production run material."""
        data = {
            "spool_id": uuid4(),
            "estimated_model_weight_grams": Decimal("100.5"),
            "estimated_flushed_grams": Decimal("10.0"),
            "cost_per_gram": Decimal("0.025"),
        }
        material = ProductionRunMaterialCreate(**data)
        assert material.estimated_model_weight_grams == Decimal("100.5")
        assert material.estimated_flushed_grams == Decimal("10.0")

    def test_production_run_material_create_invalid_weight(self):
        """Test that zero or negative weight raises ValidationError."""
        data = {
            "spool_id": uuid4(),
            "estimated_model_weight_grams": Decimal("0"),  # Invalid
            "cost_per_gram": Decimal("0.025"),
        }
        with pytest.raises(ValidationError) as exc_info:
            ProductionRunMaterialCreate(**data)
        assert "greater than 0" in str(exc_info.value)

    def test_production_run_material_response_spool_weighing(self):
        """Test computed fields with spool weighing."""
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "spool_id": uuid4(),
            "estimated_model_weight_grams": Decimal("100.0"),
            "estimated_flushed_grams": Decimal("10.0"),
            "spool_weight_before_grams": Decimal("500.0"),
            "spool_weight_after_grams": Decimal("385.0"),  # Used 115g
            "cost_per_gram": Decimal("0.025"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        material = ProductionRunMaterialResponse(**data)

        # Actual weight from weighing: 500 - 385 = 115g
        assert material.actual_weight_from_weighing == 115.0
        assert material.actual_total_weight == 115.0

        # Variance: 115 - 110 = 5g
        assert abs(material.variance_grams - 5.0) < 0.01

        # Variance %: (5 / 110) * 100 ≈ 4.55%
        assert abs(material.variance_percentage - 4.545) < 0.01

        # Total cost: 115 * 0.025 = 2.875
        assert abs(material.total_cost - 2.875) < 0.01

    def test_production_run_material_response_manual_entry(self):
        """Test computed fields with manual weight entry."""
        data = {
            "id": uuid4(),
            "production_run_id": uuid4(),
            "spool_id": uuid4(),
            "estimated_model_weight_grams": Decimal("100.0"),
            "estimated_flushed_grams": Decimal("10.0"),
            # Manual entry fields
            "actual_model_weight_grams": Decimal("95.0"),  # Manual model weight
            "actual_flushed_grams": Decimal("8.0"),  # Manual flush weight
            "actual_tower_grams": Decimal("2.0"),  # Manual tower weight
            "cost_per_gram": Decimal("0.025"),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        material = ProductionRunMaterialResponse(**data)

        # Actual weight from manual entry: 95 + 8 + 2 = 105g
        assert material.actual_total_weight == 105.0

        # Variance: 105 - 110 = -5g (under estimate)
        assert abs(material.variance_grams - (-5.0)) < 0.01

        # Variance %: (-5 / 110) * 100 ≈ -4.55%
        assert abs(material.variance_percentage - (-4.545)) < 0.01


class TestProductionRunDetailResponse:
    """Tests for detailed production run response with nested data."""

    def test_production_run_detail_response_computed_totals(self):
        """Test computed totals across items and materials."""
        # Create detail response with items and materials
        items = [
            ProductionRunItemResponse(
                id=uuid4(),
                production_run_id=uuid4(),
                model_id=uuid4(),
                quantity=10,
                successful_quantity=9,
                failed_quantity=1,
                estimated_total_cost=Decimal("50.00"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            ProductionRunItemResponse(
                id=uuid4(),
                production_run_id=uuid4(),
                model_id=uuid4(),
                quantity=5,
                successful_quantity=5,
                failed_quantity=0,
                estimated_total_cost=Decimal("30.00"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        materials = [
            ProductionRunMaterialResponse(
                id=uuid4(),
                production_run_id=uuid4(),
                spool_id=uuid4(),
                estimated_model_weight_grams=Decimal("100.0"),
                estimated_flushed_grams=Decimal("10.0"),
                actual_model_weight_grams=Decimal("105.0"),
                actual_flushed_grams=Decimal("8.0"),
                actual_tower_grams=Decimal("2.0"),
                cost_per_gram=Decimal("0.025"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            ProductionRunMaterialResponse(
                id=uuid4(),
                production_run_id=uuid4(),
                spool_id=uuid4(),
                estimated_model_weight_grams=Decimal("50.0"),
                estimated_flushed_grams=Decimal("5.0"),
                actual_model_weight_grams=Decimal("48.0"),
                actual_flushed_grams=Decimal("3.0"),
                actual_tower_grams=Decimal("1.0"),
                cost_per_gram=Decimal("0.030"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

        detail = ProductionRunDetailResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            run_number="TEST-20251113-003",
            started_at=datetime.now(),
            status="completed",
            items=items,
            materials=materials,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Total items planned: 10 + 5 = 15
        assert detail.total_items_planned == 15

        # Total successful: 9 + 5 = 14
        assert detail.total_items_successful == 14

        # Total failed: 1 + 0 = 1
        assert detail.total_items_failed == 1

        # Overall success rate: (14 / 15) * 100 ≈ 93.33%
        assert abs(detail.overall_success_rate - 93.33) < 0.01

        # Total material cost: (115 * 0.025) + (52 * 0.030) = 2.875 + 1.56 = 4.435
        assert abs(detail.total_material_cost - 4.435) < 0.001

        # Total estimated cost: 50 + 30 = 80
        assert abs(detail.total_estimated_cost - 80.0) < 0.01
