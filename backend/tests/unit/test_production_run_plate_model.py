"""Unit tests for ProductionRunPlate model."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.production_run import ProductionRun
from app.models.production_run_plate import ProductionRunPlate


class TestProductionRunPlateModel:
    """Tests for ProductionRunPlate model creation and properties."""

    @pytest.mark.asyncio
    async def test_create_plate_basic(self, db_session, test_tenant, test_model, test_printer):
        """Test creating a basic plate with required fields."""
        # Create production run first
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Dragon Bodies (A1 Mini)",
            prints_per_plate=3,
        )
        db_session.add(plate)
        await db_session.commit()
        await db_session.refresh(plate)

        assert plate.id is not None
        assert plate.production_run_id == run.id
        assert plate.model_id == test_model.id
        assert plate.printer_id == test_printer.id
        assert plate.plate_number == 1
        assert plate.plate_name == "Dragon Bodies (A1 Mini)"
        assert plate.prints_per_plate == 3
        assert plate.status == "pending"  # Default
        assert plate.quantity == 1  # Default
        assert plate.created_at is not None

    @pytest.mark.asyncio
    async def test_create_plate_all_fields(self, db_session, test_tenant, test_model, test_printer):
        """Test creating a plate with all fields populated."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-002",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        started = datetime.now(timezone.utc)
        completed = started + timedelta(hours=1)

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=5,
            plate_name="Terrarium Wall 3",
            quantity=2,
            prints_per_plate=4,
            print_time_minutes=45,
            estimated_material_weight_grams=Decimal("120.5"),
            status="complete",
            started_at=started,
            completed_at=completed,
            actual_print_time_minutes=48,
            actual_material_weight_grams=Decimal("125.0"),
            successful_prints=8,
            failed_prints=0,
            notes="Perfect print!",
        )
        db_session.add(plate)
        await db_session.commit()
        await db_session.refresh(plate)

        assert plate.quantity == 2
        assert plate.prints_per_plate == 4
        assert plate.print_time_minutes == 45
        assert plate.estimated_material_weight_grams == Decimal("120.5")
        assert plate.status == "complete"
        # SQLite doesn't preserve timezone info, so compare naive datetimes
        assert plate.started_at.replace(tzinfo=None) == started.replace(tzinfo=None)
        assert plate.completed_at.replace(tzinfo=None) == completed.replace(tzinfo=None)
        assert plate.actual_print_time_minutes == 48
        assert plate.actual_material_weight_grams == Decimal("125.0")
        assert plate.successful_prints == 8
        assert plate.failed_prints == 0
        assert plate.notes == "Perfect print!"


class TestProductionRunPlateComputedProperties:
    """Tests for ProductionRunPlate computed properties."""

    @pytest.fixture
    async def sample_plate(self, db_session, test_tenant, test_model, test_printer):
        """Create a sample plate for testing."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-003",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Test Plate",
            quantity=2,
            prints_per_plate=3,
            print_time_minutes=45,
            estimated_material_weight_grams=Decimal("90.0"),
            status="pending",
            successful_prints=0,
            failed_prints=0,
        )
        db_session.add(plate)
        await db_session.commit()
        return plate

    @pytest.mark.asyncio
    async def test_is_complete(self, sample_plate):
        """Test is_complete property."""
        assert sample_plate.is_complete is False

        sample_plate.status = "complete"
        assert sample_plate.is_complete is True

        sample_plate.status = "failed"
        assert sample_plate.is_complete is False

    @pytest.mark.asyncio
    async def test_is_pending(self, sample_plate):
        """Test is_pending property."""
        assert sample_plate.is_pending is True

        sample_plate.status = "printing"
        assert sample_plate.is_pending is False

    @pytest.mark.asyncio
    async def test_is_printing(self, sample_plate):
        """Test is_printing property."""
        assert sample_plate.is_printing is False

        sample_plate.status = "printing"
        assert sample_plate.is_printing is True

    @pytest.mark.asyncio
    async def test_total_items_expected(self, sample_plate):
        """Test total_items_expected property."""
        # quantity=2, prints_per_plate=3 → 6 items expected
        assert sample_plate.total_items_expected == 6

    @pytest.mark.asyncio
    async def test_total_items_completed(self, sample_plate):
        """Test total_items_completed property."""
        assert sample_plate.total_items_completed == 0

        sample_plate.successful_prints = 4
        assert sample_plate.total_items_completed == 4

    @pytest.mark.asyncio
    async def test_progress_percentage(self, sample_plate):
        """Test progress_percentage property."""
        # 0 successful out of 6 expected
        assert sample_plate.progress_percentage == 0.0

        sample_plate.successful_prints = 3
        # 3 out of 6 = 50%
        assert sample_plate.progress_percentage == 50.0

        sample_plate.successful_prints = 6
        # 6 out of 6 = 100%
        assert sample_plate.progress_percentage == 100.0

    @pytest.mark.asyncio
    async def test_progress_percentage_zero_expected(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test progress_percentage when expected is 0."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-004",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Zero Plate",
            quantity=0,  # Edge case
            prints_per_plate=3,
        )

        assert plate.progress_percentage == 0.0

    @pytest.mark.asyncio
    async def test_total_estimated_time_minutes(self, sample_plate):
        """Test total_estimated_time_minutes property."""
        # quantity=2, print_time=45 → 90 minutes total
        assert sample_plate.total_estimated_time_minutes == 90

    @pytest.mark.asyncio
    async def test_total_estimated_time_minutes_none(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test total_estimated_time_minutes when print_time is None."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-005",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="No Time Plate",
            quantity=2,
            prints_per_plate=3,
            print_time_minutes=None,
        )

        assert plate.total_estimated_time_minutes is None

    @pytest.mark.asyncio
    async def test_total_estimated_material_grams(self, sample_plate):
        """Test total_estimated_material_grams property."""
        # quantity=2, estimated_material=90g → 180g total
        assert sample_plate.total_estimated_material_grams == Decimal("180.0")

    @pytest.mark.asyncio
    async def test_total_estimated_material_grams_none(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test total_estimated_material_grams when material_weight is None."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-006",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="No Material Plate",
            quantity=2,
            prints_per_plate=3,
            estimated_material_weight_grams=None,
        )

        assert plate.total_estimated_material_grams is None

    @pytest.mark.asyncio
    async def test_repr(self, sample_plate):
        """Test __repr__ method."""
        repr_str = repr(sample_plate)
        assert "plate_number=1" in repr_str
        assert "Test Plate" in repr_str
        assert "pending" in repr_str


class TestProductionRunPlateConstraints:
    """Tests for ProductionRunPlate model constraints."""

    @pytest.mark.asyncio
    async def test_plate_number_positive(self, db_session, test_tenant, test_model, test_printer):
        """Test that plate_number must be positive."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-007",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=0,  # Invalid
            plate_name="Invalid Plate",
            prints_per_plate=3,
        )
        db_session.add(plate)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_quantity_positive(self, db_session, test_tenant, test_model, test_printer):
        """Test that quantity must be positive."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-008",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Invalid Quantity Plate",
            quantity=0,  # Invalid
            prints_per_plate=3,
        )
        db_session.add(plate)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_valid_status_values(self, db_session, test_tenant, test_model, test_printer):
        """Test that status must be one of valid values."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-009",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Invalid Status Plate",
            prints_per_plate=3,
            status="invalid_status",  # Invalid
        )
        db_session.add(plate)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_all_valid_statuses(self, db_session, test_tenant, test_model, test_printer):
        """Test all valid status values."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-010",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=5,
        )
        db_session.add(run)
        await db_session.commit()

        valid_statuses = ["pending", "printing", "complete", "failed", "cancelled"]

        for i, status in enumerate(valid_statuses):
            plate = ProductionRunPlate(
                id=uuid4(),
                production_run_id=run.id,
                model_id=test_model.id,
                printer_id=test_printer.id,
                plate_number=i + 1,
                plate_name=f"Status {status} Plate",
                prints_per_plate=3,
                status=status,
            )
            db_session.add(plate)

        await db_session.commit()

        result = await db_session.execute(
            select(ProductionRunPlate).where(ProductionRunPlate.production_run_id == run.id)
        )
        plates = result.scalars().all()
        assert len(plates) == 5

    @pytest.mark.asyncio
    async def test_completed_after_started_constraint(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test that completed_at must be >= started_at."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-011",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        started = datetime.now(timezone.utc)
        completed = started - timedelta(hours=1)  # Before started - invalid

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Invalid Time Plate",
            prints_per_plate=3,
            started_at=started,
            completed_at=completed,
        )
        db_session.add(plate)

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestProductionRunPlateRelationships:
    """Tests for ProductionRunPlate relationships."""

    @pytest.mark.asyncio
    async def test_plate_production_run_relationship(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test the production_run relationship."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-012",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Relationship Test Plate",
            prints_per_plate=3,
        )
        db_session.add(plate)
        await db_session.commit()
        await db_session.refresh(plate)

        assert plate.production_run is not None
        assert plate.production_run.id == run.id
        assert plate.production_run.run_number == run.run_number

    @pytest.mark.asyncio
    async def test_plate_model_relationship(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test the model relationship."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-013",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Model Relationship Plate",
            prints_per_plate=3,
        )
        db_session.add(plate)
        await db_session.commit()
        await db_session.refresh(plate)

        assert plate.model is not None
        assert plate.model.id == test_model.id

    @pytest.mark.asyncio
    async def test_plate_printer_relationship(
        self, db_session, test_tenant, test_model, test_printer
    ):
        """Test the printer relationship."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-014",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Printer Relationship Plate",
            prints_per_plate=3,
        )
        db_session.add(plate)
        await db_session.commit()
        await db_session.refresh(plate)

        assert plate.printer is not None
        assert plate.printer.id == test_printer.id
        assert plate.printer.name == test_printer.name

    @pytest.mark.asyncio
    async def test_run_plates_relationship(self, db_session, test_tenant, test_model, test_printer):
        """Test accessing plates from production run."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-015",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=3,
        )
        db_session.add(run)
        await db_session.commit()

        # Create multiple plates
        for i in range(3):
            plate = ProductionRunPlate(
                id=uuid4(),
                production_run_id=run.id,
                model_id=test_model.id,
                printer_id=test_printer.id,
                plate_number=i + 1,
                plate_name=f"Plate {i + 1}",
                prints_per_plate=3,
            )
            db_session.add(plate)

        await db_session.commit()
        await db_session.refresh(run)

        assert len(run.plates) == 3

    @pytest.mark.asyncio
    async def test_cascade_delete_on_run(self, db_session, test_tenant, test_model, test_printer):
        """Test that plates are deleted when run is deleted."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-20251215-016",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=1,
        )
        db_session.add(run)
        await db_session.commit()

        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Will Be Deleted",
            prints_per_plate=3,
        )
        db_session.add(plate)
        await db_session.commit()

        plate_id = plate.id

        # Delete run
        await db_session.delete(run)
        await db_session.commit()

        # Verify plate is deleted
        result = await db_session.execute(
            select(ProductionRunPlate).where(ProductionRunPlate.id == plate_id)
        )
        deleted_plate = result.scalar_one_or_none()
        assert deleted_plate is None
