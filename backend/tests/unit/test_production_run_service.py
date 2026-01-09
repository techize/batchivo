"""Unit tests for Production Run Service."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.spool import Spool
from app.schemas.production_run import (
    ProductionRunCreate,
    ProductionRunUpdate,
    ProductionRunItemCreate,
    ProductionRunMaterialCreate,
)
from app.services.production_run import ProductionRunService


def unique_run_number(prefix: str = "TEST") -> str:
    """Generate unique run number for tests."""
    return f"{prefix}-{uuid4().hex[:8]}"


class TestProductionRunService:
    """Tests for ProductionRunService basic operations."""

    @pytest.mark.asyncio
    async def test_create_production_run_basic(self, db_session, test_tenant):
        """Test creating a basic production run without items or materials."""
        service = ProductionRunService(db_session, test_tenant)

        data = ProductionRunCreate(
            started_at=datetime.now(),
            printer_name="Prusa i3 MK3S",
            slicer_software="PrusaSlicer",
            status="in_progress",
        )

        run = await service.create_production_run(data)

        assert run.id is not None
        assert run.tenant_id == test_tenant.id
        assert run.printer_name == "Prusa i3 MK3S"
        assert run.status == "in_progress"
        # Run number should be auto-generated
        assert run.run_number.startswith(test_tenant.slug[:4].upper())
        assert len(run.run_number) > 10  # Format: XXXX-YYYYMMDD-NNN

    @pytest.mark.asyncio
    async def test_generate_run_number_format(self, db_session, test_tenant):
        """Test run number generation format."""
        service = ProductionRunService(db_session, test_tenant)

        run_number = await service.generate_run_number()

        # Format: {tenant_short}-YYYYMMDD-NNN
        parts = run_number.split("-")
        assert len(parts) == 3
        assert parts[0] == test_tenant.slug[:4].upper()
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 3  # NNN (zero-padded)
        assert parts[2].isdigit()

    @pytest.mark.asyncio
    async def test_generate_run_number_sequential(self, db_session, test_tenant):
        """Test run number sequential incrementing."""
        service = ProductionRunService(db_session, test_tenant)

        # Create first run
        run1_number = await service.generate_run_number()
        data1 = ProductionRunCreate(
            run_number=run1_number,
            started_at=datetime.now(),
            status="in_progress",
        )
        await service.create_production_run(data1)

        # Create second run
        run2_number = await service.generate_run_number()

        # Extract sequence numbers
        seq1 = int(run1_number.split("-")[2])
        seq2 = int(run2_number.split("-")[2])

        assert seq2 == seq1 + 1

    @pytest.mark.asyncio
    async def test_get_production_run_by_id(self, db_session, test_tenant):
        """Test retrieving a production run by ID."""
        service = ProductionRunService(db_session, test_tenant)

        # Create a run
        data = ProductionRunCreate(
            run_number=unique_run_number("TEST-001"),
            started_at=datetime.now(),
            status="in_progress",
        )
        created_run = await service.create_production_run(data)

        # Retrieve it
        retrieved_run = await service.get_production_run(created_run.id)

        assert retrieved_run is not None
        assert retrieved_run.id == created_run.id
        assert retrieved_run.run_number == created_run.run_number

    @pytest.mark.asyncio
    async def test_get_production_run_by_number(self, db_session, test_tenant):
        """Test retrieving a production run by run number."""
        service = ProductionRunService(db_session, test_tenant)

        data = ProductionRunCreate(
            run_number=unique_run_number("TEST-RUN-001"),
            started_at=datetime.now(),
            status="in_progress",
        )
        created_run = await service.create_production_run(data)

        retrieved_run = await service.get_production_run_by_number(created_run.run_number)

        assert retrieved_run is not None
        assert retrieved_run.id == created_run.id

    @pytest.mark.asyncio
    async def test_list_production_runs_pagination(self, db_session, test_tenant):
        """Test listing production runs with pagination."""
        service = ProductionRunService(db_session, test_tenant)

        # Create 5 runs
        for i in range(5):
            data = ProductionRunCreate(
                run_number=f"TEST-{i:03d}",
                started_at=datetime.now() - timedelta(hours=i),
                status="completed" if i < 3 else "in_progress",
            )
            await service.create_production_run(data)

        # Get first page
        runs, total = await service.list_production_runs(page=1, page_size=2)

        assert total == 5
        assert len(runs) == 2

        # Get second page
        runs, total = await service.list_production_runs(page=2, page_size=2)

        assert total == 5
        assert len(runs) == 2

    @pytest.mark.asyncio
    async def test_list_production_runs_filter_by_status(self, db_session, test_tenant):
        """Test filtering production runs by status."""
        service = ProductionRunService(db_session, test_tenant)

        # Create runs with different statuses
        for status in ["completed", "in_progress", "completed"]:
            data = ProductionRunCreate(
                run_number=unique_run_number(f"TEST-{status}"),
                started_at=datetime.now(),
                status=status,
            )
            await service.create_production_run(data)

        # Filter by completed
        runs, total = await service.list_production_runs(status="completed")

        assert total == 2
        assert all(run.status == "completed" for run in runs)

    @pytest.mark.asyncio
    async def test_update_production_run(self, db_session, test_tenant):
        """Test updating a production run."""
        service = ProductionRunService(db_session, test_tenant)

        # Create a run
        data = ProductionRunCreate(
            run_number=unique_run_number("TEST-UPDATE"),
            started_at=datetime.now(),
            status="in_progress",
        )
        run = await service.create_production_run(data)

        # Update it
        update_data = ProductionRunUpdate(
            quality_rating=5,
            quality_notes="Perfect print!",
        )
        updated_run = await service.update_production_run(run.id, update_data)

        assert updated_run.quality_rating == 5
        assert updated_run.quality_notes == "Perfect print!"

    @pytest.mark.asyncio
    async def test_delete_production_run(self, db_session, test_tenant):
        """Test deleting a production run."""
        service = ProductionRunService(db_session, test_tenant)

        # Create a run
        data = ProductionRunCreate(
            run_number=unique_run_number("TEST-DELETE"),
            started_at=datetime.now(),
            status="in_progress",
        )
        run = await service.create_production_run(data)

        # Delete it
        result = await service.delete_production_run(run.id)

        assert result is True

        # Verify deletion
        deleted_run = await service.get_production_run(run.id)
        assert deleted_run is None


class TestProductionRunItems:
    """Tests for production run item management."""

    @pytest.mark.asyncio
    async def test_create_run_with_items(self, db_session, test_tenant, test_model):
        """Test creating a production run with items."""
        service = ProductionRunService(db_session, test_tenant)

        item_data = ProductionRunItemCreate(
            model_id=test_model.id,  # model_id references models table
            quantity=10,
            bed_position="front-left",
            estimated_total_cost=Decimal("50.00"),
        )

        run_data = ProductionRunCreate(
            run_number=unique_run_number("TEST-ITEMS-001"),
            started_at=datetime.now(),
            status="in_progress",
        )

        run = await service.create_production_run(run_data, items=[item_data])

        assert len(run.items) == 1
        assert run.items[0].quantity == 10
        assert run.items[0].model_id == test_model.id

    @pytest.mark.asyncio
    async def test_add_item_to_existing_run(self, db_session, test_tenant, test_model):
        """Test adding an item to an existing production run."""
        service = ProductionRunService(db_session, test_tenant)

        # Create run
        run_data = ProductionRunCreate(
            run_number=unique_run_number("TEST-ADD-ITEM"),
            started_at=datetime.now(),
            status="in_progress",
        )
        run = await service.create_production_run(run_data)

        # Add item
        item_data = ProductionRunItemCreate(
            model_id=test_model.id,  # model_id references models table
            quantity=5,
        )
        item = await service.add_item_to_run(run.id, item_data)

        assert item is not None
        assert item.quantity == 5


class TestProductionRunMaterials:
    """Tests for production run material management."""

    @pytest.mark.asyncio
    async def test_create_run_with_materials(self, db_session, test_tenant, test_spool):
        """Test creating a production run with materials."""
        service = ProductionRunService(db_session, test_tenant)

        material_data = ProductionRunMaterialCreate(
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            cost_per_gram=Decimal("0.025"),
        )

        run_data = ProductionRunCreate(
            run_number=unique_run_number("TEST-MATERIALS-001"),
            started_at=datetime.now(),
            status="in_progress",
        )

        run = await service.create_production_run(run_data, materials=[material_data])

        assert len(run.materials) == 1
        assert run.materials[0].estimated_model_weight_grams == Decimal("100.0")
        assert run.materials[0].spool_id == test_spool.id

    @pytest.mark.asyncio
    async def test_add_material_to_existing_run(self, db_session, test_tenant, test_spool):
        """Test adding a material to an existing production run."""
        service = ProductionRunService(db_session, test_tenant)

        # Create run
        run_data = ProductionRunCreate(
            run_number=unique_run_number("TEST-ADD-MATERIAL"),
            started_at=datetime.now(),
            status="in_progress",
        )
        run = await service.create_production_run(run_data)

        # Add material
        material_data = ProductionRunMaterialCreate(
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("50.0"),
            estimated_flushed_grams=Decimal("5.0"),
            cost_per_gram=Decimal("0.020"),
        )
        material = await service.add_material_to_run(run.id, material_data)

        assert material is not None
        assert material.estimated_model_weight_grams == Decimal("50.0")


class TestProductionRunCompletion:
    """Tests for production run completion and inventory integration."""

    @pytest.mark.asyncio
    async def test_complete_production_run_deducts_inventory(
        self, db_session, test_tenant, test_spool
    ):
        """Test that completing a run deducts from spool inventory."""
        service = ProductionRunService(db_session, test_tenant)

        # Get initial spool weight
        initial_weight = test_spool.current_weight

        # Create run with material
        material_data = ProductionRunMaterialCreate(
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            spool_weight_before_grams=Decimal("200.0"),
            spool_weight_after_grams=Decimal("95.0"),
            cost_per_gram=Decimal("0.025"),
        )

        run_data = ProductionRunCreate(
            run_number=unique_run_number("TEST-COMPLETE"),
            started_at=datetime.now(),
            status="in_progress",
        )

        run = await service.create_production_run(run_data, materials=[material_data])

        # Complete the run
        completed_run = await service.complete_production_run(run.id)

        assert completed_run.status == "completed"
        assert completed_run.completed_at is not None

        # Verify spool weight was deducted
        result = await db_session.execute(select(Spool).where(Spool.id == test_spool.id))
        updated_spool = result.scalar_one()

        expected_weight = float(Decimal(str(initial_weight)) - Decimal("105.0"))
        assert abs(float(updated_spool.current_weight) - expected_weight) < 0.01

    @pytest.mark.asyncio
    async def test_complete_run_insufficient_weight_raises_error(
        self, db_session, test_tenant, test_spool
    ):
        """Test that completing a run with insufficient spool weight raises an error."""
        service = ProductionRunService(db_session, test_tenant)

        # Set spool weight to a low value
        test_spool.current_weight = 50.0
        db_session.add(test_spool)
        await db_session.commit()

        # Create run requiring more weight than available
        material_data = ProductionRunMaterialCreate(
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            spool_weight_before_grams=Decimal("200.0"),
            spool_weight_after_grams=Decimal("100.0"),
            cost_per_gram=Decimal("0.025"),
        )

        run_data = ProductionRunCreate(
            run_number=unique_run_number("TEST-INSUFFICIENT"),
            started_at=datetime.now(),
            status="in_progress",
        )

        run = await service.create_production_run(run_data, materials=[material_data])

        # Attempt to complete should raise error
        with pytest.raises(ValueError, match="Insufficient weight"):
            await service.complete_production_run(run.id)

    @pytest.mark.asyncio
    async def test_revert_completion_returns_inventory(self, db_session, test_tenant, test_spool):
        """Test that reverting completion returns material to inventory."""
        service = ProductionRunService(db_session, test_tenant)

        initial_weight = test_spool.current_weight

        # Create and complete run
        material_data = ProductionRunMaterialCreate(
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            spool_weight_before_grams=Decimal("200.0"),
            spool_weight_after_grams=Decimal("95.0"),
            cost_per_gram=Decimal("0.025"),
        )

        run_data = ProductionRunCreate(
            run_number=unique_run_number("TEST-REVERT"),
            started_at=datetime.now(),
            status="in_progress",
        )

        run = await service.create_production_run(run_data, materials=[material_data])
        await service.complete_production_run(run.id)

        # Revert completion
        reverted_run = await service.revert_completion(run.id)

        assert reverted_run.status == "in_progress"

        # Verify weight returned to spool
        result = await db_session.execute(select(Spool).where(Spool.id == test_spool.id))
        updated_spool = result.scalar_one()

        assert abs(float(updated_spool.current_weight) - float(initial_weight)) < 0.01


class TestVarianceCalculations:
    """Tests for variance calculation methods."""

    @pytest.mark.asyncio
    async def test_calculate_run_variance(self, db_session, test_tenant, test_spool, test_model):
        """Test calculating variance for a single run."""
        service = ProductionRunService(db_session, test_tenant)

        # Create run with items and materials
        item_data = ProductionRunItemCreate(
            model_id=test_model.id,  # model_id references models table, not products
            quantity=10,
            successful_quantity=9,
            failed_quantity=1,
        )

        material_data = ProductionRunMaterialCreate(
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            spool_weight_before_grams=Decimal("200.0"),
            spool_weight_after_grams=Decimal("85.0"),
            cost_per_gram=Decimal("0.025"),
        )

        run_data = ProductionRunCreate(
            run_number=unique_run_number("TEST-VARIANCE"),
            started_at=datetime.now(),
            estimated_print_time_hours=Decimal("4.0"),
            duration_hours=Decimal("4.5"),
            status="completed",
        )

        run = await service.create_production_run(
            run_data, items=[item_data], materials=[material_data]
        )

        # Calculate variance
        variance = await service.calculate_run_variance(run.id)

        assert variance is not None
        assert variance["weight_variance"]["total_estimated_grams"] == 110.0  # 100 + 10
        assert variance["weight_variance"]["total_actual_grams"] == 115.0
        assert variance["weight_variance"]["variance_grams"] == 5.0
        assert variance["time_variance"]["variance_hours"] == 0.5
        assert variance["success_rate"]["success_rate_percentage"] == 90.0

    @pytest.mark.asyncio
    async def test_calculate_aggregate_variance(self, db_session, test_tenant, test_spool):
        """Test calculating aggregate variance across multiple runs."""
        service = ProductionRunService(db_session, test_tenant)

        # Create 3 completed runs
        for i in range(3):
            material_data = ProductionRunMaterialCreate(
                spool_id=test_spool.id,
                estimated_model_weight_grams=Decimal("100.0"),
                estimated_flushed_grams=Decimal("10.0"),
                spool_weight_before_grams=Decimal("200.0"),
                spool_weight_after_grams=Decimal("95.0"),
                cost_per_gram=Decimal("0.025"),
            )

            run_data = ProductionRunCreate(
                run_number=f"TEST-AGG-{i:03d}",
                started_at=datetime.now(),
                estimated_print_time_hours=Decimal("4.0"),
                duration_hours=Decimal("4.2"),
                status="completed",
            )

            await service.create_production_run(run_data, materials=[material_data])

        # Calculate aggregate
        aggregate = await service.calculate_aggregate_variance(status="completed")

        assert aggregate["runs_analyzed"] == 3
        assert aggregate["aggregate_weight_variance"]["total_estimated_grams"] == 330.0  # 3 * 110
        assert aggregate["aggregate_weight_variance"]["total_actual_grams"] == 315.0  # 3 * 105
        assert aggregate["aggregate_time_variance"]["runs_with_data"] == 3
