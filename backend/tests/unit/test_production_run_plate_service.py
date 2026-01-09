"""Unit tests for ProductionRunPlateService."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.production_run import ProductionRun
from app.models.production_run_plate import ProductionRunPlate
from app.schemas.production_run_plate import (
    ProductionRunPlateCreate,
    ProductionRunPlateUpdate,
    MarkPlateCompleteRequest,
)
from app.services.production_run_plate_service import ProductionRunPlateService


@pytest.fixture
async def test_production_run(db_session, test_tenant):
    """Create a test production run."""
    run = ProductionRun(
        id=uuid4(),
        tenant_id=test_tenant.id,
        run_number=f"TEST-{uuid4().hex[:8]}",
        started_at=datetime.now(timezone.utc),
        status="in_progress",
        total_plates=0,
        completed_plates=0,
    )
    db_session.add(run)
    await db_session.commit()
    await db_session.refresh(run)
    return run


@pytest.fixture
async def test_plate(db_session, test_tenant, test_production_run, test_model, test_printer):
    """Create a test production run plate."""
    plate = ProductionRunPlate(
        id=uuid4(),
        production_run_id=test_production_run.id,
        model_id=test_model.id,
        printer_id=test_printer.id,
        plate_name="Test Plate",
        plate_number=1,
        status="pending",
        prints_per_plate=4,
    )
    db_session.add(plate)
    await db_session.commit()
    await db_session.refresh(plate)
    return plate


class TestProductionRunPlateServiceCreate:
    """Tests for plate creation."""

    @pytest.mark.asyncio
    async def test_create_plate_basic(
        self, db_session, test_tenant, test_production_run, test_model, test_printer
    ):
        """Test creating a basic plate."""
        service = ProductionRunPlateService(db_session, test_tenant)

        data = ProductionRunPlateCreate(
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_name="New Plate",
            plate_number=1,
            prints_per_plate=4,
        )

        plate = await service.create_plate(test_production_run.id, data)

        assert plate.id is not None
        assert plate.production_run_id == test_production_run.id
        assert plate.model_id == test_model.id
        assert plate.printer_id == test_printer.id
        assert plate.plate_name == "New Plate"
        assert plate.plate_number == 1
        assert plate.prints_per_plate == 4
        assert plate.status == "pending"

    @pytest.mark.asyncio
    async def test_create_plate_full_details(
        self, db_session, test_tenant, test_production_run, test_model, test_printer
    ):
        """Test creating a plate with all fields."""
        service = ProductionRunPlateService(db_session, test_tenant)

        data = ProductionRunPlateCreate(
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_name="Full Plate",
            plate_number=1,
            prints_per_plate=6,
            print_time_minutes=90,
            estimated_material_weight_grams=Decimal("45.5"),
            notes="Test notes for plate",
        )

        plate = await service.create_plate(test_production_run.id, data)

        assert plate.plate_name == "Full Plate"
        assert plate.prints_per_plate == 6
        assert plate.print_time_minutes == 90
        assert plate.estimated_material_weight_grams == Decimal("45.5")
        assert plate.notes == "Test notes for plate"

    @pytest.mark.asyncio
    async def test_create_plate_updates_run_counts(
        self, db_session, test_tenant, test_production_run, test_model, test_printer
    ):
        """Test that creating a plate updates the run's plate counts."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Initially no plates
        result = await db_session.execute(
            select(ProductionRun).where(ProductionRun.id == test_production_run.id)
        )
        run = result.scalar_one()
        assert run.total_plates == 0

        # Create a plate
        data = ProductionRunPlateCreate(
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_name="Count Test",
            plate_number=1,
            prints_per_plate=4,
        )
        await service.create_plate(test_production_run.id, data)

        # Check count updated
        await db_session.refresh(run)
        assert run.total_plates == 1
        assert run.completed_plates == 0

    @pytest.mark.asyncio
    async def test_create_plate_invalid_run(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test creating plate for non-existent run raises error."""
        service = ProductionRunPlateService(db_session, test_tenant)

        data = ProductionRunPlateCreate(
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_name="Invalid Run Plate",
            plate_number=1,
            prints_per_plate=4,
        )

        with pytest.raises(ValueError, match="Production run.*not found"):
            await service.create_plate(uuid4(), data)

    @pytest.mark.asyncio
    async def test_create_plate_invalid_model(
        self, db_session, test_tenant, test_production_run, test_printer
    ):
        """Test creating plate with non-existent model raises error."""
        service = ProductionRunPlateService(db_session, test_tenant)

        data = ProductionRunPlateCreate(
            model_id=uuid4(),  # Invalid model
            printer_id=test_printer.id,
            plate_name="Invalid Model Plate",
            plate_number=1,
            prints_per_plate=4,
        )

        with pytest.raises(ValueError, match="Model.*not found"):
            await service.create_plate(test_production_run.id, data)

    @pytest.mark.asyncio
    async def test_create_plate_invalid_printer(
        self, db_session, test_tenant, test_production_run, test_model
    ):
        """Test creating plate with non-existent printer raises error."""
        service = ProductionRunPlateService(db_session, test_tenant)

        data = ProductionRunPlateCreate(
            model_id=test_model.id,
            printer_id=uuid4(),  # Invalid printer
            plate_name="Invalid Printer Plate",
            plate_number=1,
            prints_per_plate=4,
        )

        with pytest.raises(ValueError, match="Printer.*not found"):
            await service.create_plate(test_production_run.id, data)


class TestProductionRunPlateServiceRead:
    """Tests for plate retrieval."""

    @pytest.mark.asyncio
    async def test_get_plate_by_id(self, db_session, test_tenant, test_plate):
        """Test retrieving a plate by ID."""
        service = ProductionRunPlateService(db_session, test_tenant)

        plate = await service.get_plate(test_plate.id)

        assert plate is not None
        assert plate.id == test_plate.id
        assert plate.plate_name == test_plate.plate_name

    @pytest.mark.asyncio
    async def test_get_plate_not_found(self, db_session, test_tenant):
        """Test retrieving non-existent plate returns None."""
        service = ProductionRunPlateService(db_session, test_tenant)

        plate = await service.get_plate(uuid4())

        assert plate is None

    @pytest.mark.asyncio
    async def test_get_plate_tenant_isolation(self, db_session, test_tenant, test_plate):
        """Test that plate retrieval respects tenant isolation."""
        # Create another tenant
        from app.models.tenant import Tenant

        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant",
            slug="other-tenant",
        )
        db_session.add(other_tenant)
        await db_session.commit()

        other_service = ProductionRunPlateService(db_session, other_tenant)

        # Other tenant shouldn't see the plate
        plate = await other_service.get_plate(test_plate.id)

        assert plate is None


class TestProductionRunPlateServiceList:
    """Tests for listing plates."""

    @pytest.mark.asyncio
    async def test_list_plates_for_run(
        self, db_session, test_tenant, test_production_run, test_model, test_printer
    ):
        """Test listing plates for a production run."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Create multiple plates
        for i in range(3):
            data = ProductionRunPlateCreate(
                model_id=test_model.id,
                printer_id=test_printer.id,
                plate_name=f"Plate {i}",
                plate_number=i + 1,
                prints_per_plate=4,
            )
            await service.create_plate(test_production_run.id, data)

        result = await service.list_plates_for_run(test_production_run.id)

        assert result.total == 3
        assert len(result.plates) == 3

    @pytest.mark.asyncio
    async def test_list_plates_empty(self, db_session, test_tenant, test_production_run):
        """Test listing plates when none exist."""
        service = ProductionRunPlateService(db_session, test_tenant)

        result = await service.list_plates_for_run(test_production_run.id)

        assert result.total == 0
        assert result.plates == []

    @pytest.mark.asyncio
    async def test_list_plates_filter_by_status(
        self, db_session, test_tenant, test_production_run, test_model, test_printer
    ):
        """Test filtering plates by status."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Create plates with different statuses
        statuses = ["pending", "printing", "complete"]
        for i, status in enumerate(statuses):
            plate = ProductionRunPlate(
                id=uuid4(),
                production_run_id=test_production_run.id,
                model_id=test_model.id,
                printer_id=test_printer.id,
                plate_name=f"Plate {i}",
                plate_number=i + 1,
                status=status,
                prints_per_plate=4,
            )
            db_session.add(plate)
        await db_session.commit()

        # Filter by pending
        result = await service.list_plates_for_run(test_production_run.id, status="pending")

        assert result.total == 1
        assert result.plates[0].status == "pending"

    @pytest.mark.asyncio
    async def test_list_plates_pagination(
        self, db_session, test_tenant, test_production_run, test_model, test_printer
    ):
        """Test listing plates with pagination."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Create 5 plates
        for i in range(5):
            data = ProductionRunPlateCreate(
                model_id=test_model.id,
                printer_id=test_printer.id,
                plate_name=f"Plate {i}",
                plate_number=i + 1,
                prints_per_plate=4,
            )
            await service.create_plate(test_production_run.id, data)

        result = await service.list_plates_for_run(test_production_run.id, skip=0, limit=2)

        assert result.total == 5
        assert len(result.plates) == 2
        assert result.skip == 0
        assert result.limit == 2

    @pytest.mark.asyncio
    async def test_list_plates_ordered_by_plate_number(
        self, db_session, test_tenant, test_production_run, test_model, test_printer
    ):
        """Test that plates are ordered by plate number."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Create plates out of order
        for plate_num in [3, 1, 2]:
            data = ProductionRunPlateCreate(
                model_id=test_model.id,
                printer_id=test_printer.id,
                plate_name=f"Plate {plate_num}",
                plate_number=plate_num,
                prints_per_plate=4,
            )
            await service.create_plate(test_production_run.id, data)

        result = await service.list_plates_for_run(test_production_run.id)

        plate_numbers = [p.plate_number for p in result.plates]
        assert plate_numbers == [1, 2, 3]


class TestProductionRunPlateServiceUpdate:
    """Tests for plate updates."""

    @pytest.mark.asyncio
    async def test_update_plate_single_field(self, db_session, test_tenant, test_plate):
        """Test updating a single field."""
        service = ProductionRunPlateService(db_session, test_tenant)

        update = ProductionRunPlateUpdate(notes="Single field update")
        updated = await service.update_plate(test_plate.id, update)

        assert updated is not None
        assert updated.notes == "Single field update"

    @pytest.mark.asyncio
    async def test_update_plate_multiple_fields(self, db_session, test_tenant, test_plate):
        """Test updating multiple fields."""
        service = ProductionRunPlateService(db_session, test_tenant)

        update = ProductionRunPlateUpdate(
            notes="Updated notes",
            successful_prints=3,
            failed_prints=1,
        )
        updated = await service.update_plate(test_plate.id, update)

        assert updated.notes == "Updated notes"
        assert updated.successful_prints == 3
        assert updated.failed_prints == 1

    @pytest.mark.asyncio
    async def test_update_plate_not_found(self, db_session, test_tenant):
        """Test updating non-existent plate returns None."""
        service = ProductionRunPlateService(db_session, test_tenant)

        update = ProductionRunPlateUpdate(plate_name="Not Found")
        result = await service.update_plate(uuid4(), update)

        assert result is None


class TestProductionRunPlateServiceStatusTransitions:
    """Tests for plate status transitions."""

    @pytest.mark.asyncio
    async def test_start_plate(self, db_session, test_tenant, test_plate):
        """Test starting a plate (pending -> printing)."""
        service = ProductionRunPlateService(db_session, test_tenant)

        started = await service.start_plate(test_plate.id)

        assert started.status == "printing"
        assert started.started_at is not None

    @pytest.mark.asyncio
    async def test_start_plate_invalid_status(self, db_session, test_tenant, test_plate):
        """Test starting a plate that's not pending raises error."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Start it first
        await service.start_plate(test_plate.id)

        # Try to start again
        with pytest.raises(ValueError, match="Cannot start plate"):
            await service.start_plate(test_plate.id)

    @pytest.mark.asyncio
    async def test_complete_plate(self, db_session, test_tenant, test_plate):
        """Test completing a plate."""
        service = ProductionRunPlateService(db_session, test_tenant)

        data = MarkPlateCompleteRequest(
            successful_prints=3,
            failed_prints=1,
            actual_print_time_minutes=55,
            actual_material_weight_grams=Decimal("42.5"),
            notes="Completion notes",
        )

        completed = await service.complete_plate(test_plate.id, data)

        assert completed.status == "complete"
        assert completed.completed_at is not None
        assert completed.successful_prints == 3
        assert completed.failed_prints == 1
        assert completed.actual_print_time_minutes == 55
        assert completed.actual_material_weight_grams == Decimal("42.5")
        assert completed.notes == "Completion notes"

    @pytest.mark.asyncio
    async def test_complete_plate_from_printing(self, db_session, test_tenant, test_plate):
        """Test completing a plate that's printing."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Start first
        await service.start_plate(test_plate.id)

        # Then complete
        data = MarkPlateCompleteRequest(
            successful_prints=4,
            failed_prints=0,
        )
        completed = await service.complete_plate(test_plate.id, data)

        assert completed.status == "complete"

    @pytest.mark.asyncio
    async def test_complete_plate_updates_run_counts(
        self, db_session, test_tenant, test_production_run, test_plate
    ):
        """Test that completing a plate updates run's completed count."""
        service = ProductionRunPlateService(db_session, test_tenant)

        data = MarkPlateCompleteRequest(
            successful_prints=4,
            failed_prints=0,
        )
        await service.complete_plate(test_plate.id, data)

        # Check run counts updated
        result = await db_session.execute(
            select(ProductionRun).where(ProductionRun.id == test_production_run.id)
        )
        run = result.scalar_one()
        assert run.completed_plates == 1

    @pytest.mark.asyncio
    async def test_complete_plate_invalid_status(self, db_session, test_tenant, test_plate):
        """Test completing already complete plate raises error."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Complete first
        data = MarkPlateCompleteRequest(successful_prints=4, failed_prints=0)
        await service.complete_plate(test_plate.id, data)

        # Try to complete again
        with pytest.raises(ValueError, match="Cannot complete plate"):
            await service.complete_plate(test_plate.id, data)

    @pytest.mark.asyncio
    async def test_fail_plate(self, db_session, test_tenant, test_plate):
        """Test failing a plate."""
        service = ProductionRunPlateService(db_session, test_tenant)

        failed = await service.fail_plate(test_plate.id, notes="Print detached")

        assert failed.status == "failed"
        assert failed.completed_at is not None
        assert failed.notes == "Print detached"

    @pytest.mark.asyncio
    async def test_fail_plate_from_printing(self, db_session, test_tenant, test_plate):
        """Test failing a plate that's printing."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Start first
        await service.start_plate(test_plate.id)

        # Then fail
        failed = await service.fail_plate(test_plate.id)

        assert failed.status == "failed"

    @pytest.mark.asyncio
    async def test_fail_complete_plate_raises_error(self, db_session, test_tenant, test_plate):
        """Test failing a completed plate raises error."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Complete first
        data = MarkPlateCompleteRequest(successful_prints=4, failed_prints=0)
        await service.complete_plate(test_plate.id, data)

        # Try to fail
        with pytest.raises(ValueError, match="Cannot fail a completed plate"):
            await service.fail_plate(test_plate.id)

    @pytest.mark.asyncio
    async def test_cancel_plate(self, db_session, test_tenant, test_plate):
        """Test cancelling a plate."""
        service = ProductionRunPlateService(db_session, test_tenant)

        cancelled = await service.cancel_plate(test_plate.id, notes="No longer needed")

        assert cancelled.status == "cancelled"
        assert cancelled.notes == "No longer needed"

    @pytest.mark.asyncio
    async def test_cancel_complete_plate_raises_error(self, db_session, test_tenant, test_plate):
        """Test cancelling a completed plate raises error."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Complete first
        data = MarkPlateCompleteRequest(successful_prints=4, failed_prints=0)
        await service.complete_plate(test_plate.id, data)

        # Try to cancel
        with pytest.raises(ValueError, match="Cannot cancel a completed plate"):
            await service.cancel_plate(test_plate.id)


class TestProductionRunPlateServiceDelete:
    """Tests for plate deletion."""

    @pytest.mark.asyncio
    async def test_delete_plate(self, db_session, test_tenant, test_plate):
        """Test deleting a plate."""
        service = ProductionRunPlateService(db_session, test_tenant)
        plate_id = test_plate.id

        result = await service.delete_plate(plate_id)

        assert result is True

        # Verify deletion
        plate = await service.get_plate(plate_id)
        assert plate is None

    @pytest.mark.asyncio
    async def test_delete_plate_not_found(self, db_session, test_tenant):
        """Test deleting non-existent plate returns False."""
        service = ProductionRunPlateService(db_session, test_tenant)

        result = await service.delete_plate(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_plate_updates_run_counts(
        self, db_session, test_tenant, test_production_run, test_plate
    ):
        """Test that deleting a plate updates run's plate counts."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # First update run to have correct count
        result = await db_session.execute(
            select(ProductionRun).where(ProductionRun.id == test_production_run.id)
        )
        run = result.scalar_one()
        run.total_plates = 1
        await db_session.commit()

        # Delete plate
        await service.delete_plate(test_plate.id)

        # Check count updated
        await db_session.refresh(run)
        assert run.total_plates == 0


class TestProductionRunPlateServiceNextPlateNumber:
    """Tests for next plate number generation."""

    @pytest.mark.asyncio
    async def test_get_next_plate_number_empty(self, db_session, test_tenant, test_production_run):
        """Test getting next plate number when no plates exist."""
        service = ProductionRunPlateService(db_session, test_tenant)

        next_num = await service.get_next_plate_number(test_production_run.id)

        assert next_num == 1

    @pytest.mark.asyncio
    async def test_get_next_plate_number_sequential(
        self, db_session, test_tenant, test_production_run, test_model, test_printer
    ):
        """Test getting next plate number increments correctly."""
        service = ProductionRunPlateService(db_session, test_tenant)

        # Create some plates
        for i in range(3):
            data = ProductionRunPlateCreate(
                model_id=test_model.id,
                printer_id=test_printer.id,
                plate_name=f"Plate {i}",
                plate_number=i + 1,
                prints_per_plate=4,
            )
            await service.create_plate(test_production_run.id, data)

        next_num = await service.get_next_plate_number(test_production_run.id)

        assert next_num == 4


class TestProductionRunPlateServiceRelationships:
    """Tests for plate relationship loading."""

    @pytest.mark.asyncio
    async def test_plate_loads_model_relationship(self, db_session, test_tenant, test_plate):
        """Test that plate loads model relationship."""
        service = ProductionRunPlateService(db_session, test_tenant)

        plate = await service.get_plate(test_plate.id)

        assert plate.model is not None
        assert plate.model.id == test_plate.model_id

    @pytest.mark.asyncio
    async def test_plate_loads_printer_relationship(self, db_session, test_tenant, test_plate):
        """Test that plate loads printer relationship."""
        service = ProductionRunPlateService(db_session, test_tenant)

        plate = await service.get_plate(test_plate.id)

        assert plate.printer is not None
        assert plate.printer.id == test_plate.printer_id

    @pytest.mark.asyncio
    async def test_plate_loads_production_run_relationship(
        self, db_session, test_tenant, test_plate
    ):
        """Test that plate loads production run relationship."""
        service = ProductionRunPlateService(db_session, test_tenant)

        plate = await service.get_plate(test_plate.id)

        assert plate.production_run is not None
        assert plate.production_run.id == test_plate.production_run_id
