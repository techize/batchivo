"""Unit tests for ProductionRun multi-plate features."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.production_run import ProductionRun, ProductionRunItem
from app.models.production_run_plate import ProductionRunPlate


class TestProductionRunMultiPlateFields:
    """Tests for new multi-plate fields on ProductionRun."""

    @pytest.mark.asyncio
    async def test_production_run_with_printer(self, db_session, test_tenant, test_printer):
        """Test creating production run with printer_id."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            printer_id=test_printer.id,
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.printer_id == test_printer.id
        assert run.printer is not None
        assert run.printer.name == test_printer.name

    @pytest.mark.asyncio
    async def test_production_run_with_product(self, db_session, test_tenant, test_product):
        """Test creating production run with product_id."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-002",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            product_id=test_product.id,
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.product_id == test_product.id
        assert run.product is not None
        assert run.product.name == test_product.name

    @pytest.mark.asyncio
    async def test_production_run_plate_tracking_fields(self, db_session, test_tenant):
        """Test total_plates and completed_plates fields."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-003",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=37,
            completed_plates=15,
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.total_plates == 37
        assert run.completed_plates == 15

    @pytest.mark.asyncio
    async def test_plate_tracking_defaults(self, db_session, test_tenant):
        """Test that plate tracking fields default to 0."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-004",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.total_plates == 0
        assert run.completed_plates == 0


class TestProductionRunMultiPlateComputedProperties:
    """Tests for ProductionRun computed properties related to multi-plate."""

    @pytest.mark.asyncio
    async def test_is_multi_plate_true(self, db_session, test_tenant):
        """Test is_multi_plate returns True when total_plates > 0."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-005",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=37,
        )

        assert run.is_multi_plate is True

    @pytest.mark.asyncio
    async def test_is_multi_plate_false(self, db_session, test_tenant):
        """Test is_multi_plate returns False when total_plates = 0."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-006",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=0,
        )

        assert run.is_multi_plate is False

    @pytest.mark.asyncio
    async def test_plates_progress_percentage_empty(self, db_session, test_tenant):
        """Test progress percentage when no plates."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-007",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=0,
            completed_plates=0,
        )

        assert run.plates_progress_percentage == 0.0

    @pytest.mark.asyncio
    async def test_plates_progress_percentage_partial(self, db_session, test_tenant):
        """Test progress percentage when partially complete."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-008",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=37,
            completed_plates=15,
        )

        # 15/37 ≈ 40.54%
        assert abs(run.plates_progress_percentage - 40.54) < 0.1

    @pytest.mark.asyncio
    async def test_plates_progress_percentage_complete(self, db_session, test_tenant):
        """Test progress percentage when fully complete."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-009",
            started_at=datetime.now(timezone.utc),
            status="completed",
            total_plates=37,
            completed_plates=37,
        )

        assert run.plates_progress_percentage == 100.0

    @pytest.mark.asyncio
    async def test_is_all_plates_complete_false_not_multi_plate(self, db_session, test_tenant):
        """Test is_all_plates_complete returns False for non-multi-plate runs."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-010",
            started_at=datetime.now(timezone.utc),
            status="completed",
            total_plates=0,
            completed_plates=0,
        )

        assert run.is_all_plates_complete is False

    @pytest.mark.asyncio
    async def test_is_all_plates_complete_false_incomplete(self, db_session, test_tenant):
        """Test is_all_plates_complete returns False when not all done."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-011",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=37,
            completed_plates=36,
        )

        assert run.is_all_plates_complete is False

    @pytest.mark.asyncio
    async def test_is_all_plates_complete_true(self, db_session, test_tenant):
        """Test is_all_plates_complete returns True when all done."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-012",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=37,
            completed_plates=37,
        )

        assert run.is_all_plates_complete is True


class TestProductionRunPlatesRelationship:
    """Tests for ProductionRun.plates relationship."""

    @pytest.mark.asyncio
    async def test_run_plates_relationship(self, db_session, test_tenant, test_model, test_printer):
        """Test accessing plates from production run."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-013",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=3,
        )
        db_session.add(run)
        await db_session.commit()

        # Create plates
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
    async def test_plates_cascade_delete(self, db_session, test_tenant, test_model, test_printer):
        """Test that plates are deleted when run is deleted."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-014",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=2,
        )
        db_session.add(run)
        await db_session.commit()

        plate_ids = []
        for i in range(2):
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
            plate_ids.append(plate.id)

        await db_session.commit()

        # Delete run
        await db_session.delete(run)
        await db_session.commit()

        # Verify plates are deleted
        for plate_id in plate_ids:
            result = await db_session.execute(
                select(ProductionRunPlate).where(ProductionRunPlate.id == plate_id)
            )
            deleted_plate = result.scalar_one_or_none()
            assert deleted_plate is None


class TestProductionRunPrinterRelationship:
    """Tests for ProductionRun.printer relationship."""

    @pytest.mark.asyncio
    async def test_printer_relationship(self, db_session, test_tenant, test_printer):
        """Test the printer relationship."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-015",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            printer_id=test_printer.id,
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.printer is not None
        assert run.printer.id == test_printer.id
        assert run.printer.name == test_printer.name

    @pytest.mark.asyncio
    async def test_printer_set_null_on_delete(self, db_session, test_tenant):
        """Test that printer_id is set to NULL when printer is deleted."""
        from app.models.printer import Printer

        # Create a deletable printer
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Deletable Printer",
        )
        db_session.add(printer)
        await db_session.commit()

        # Create run using that printer
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-016",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            printer_id=printer.id,
        )
        db_session.add(run)
        await db_session.commit()

        run_id = run.id

        # Delete printer
        await db_session.delete(printer)
        await db_session.commit()

        # Verify run still exists but printer_id is NULL
        result = await db_session.execute(select(ProductionRun).where(ProductionRun.id == run_id))
        updated_run = result.scalar_one()
        assert updated_run.printer_id is None


class TestProductionRunProductRelationship:
    """Tests for ProductionRun.product relationship."""

    @pytest.mark.asyncio
    async def test_product_relationship(self, db_session, test_tenant, test_product):
        """Test the product relationship."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-017",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            product_id=test_product.id,
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.product is not None
        assert run.product.id == test_product.id
        assert run.product.name == test_product.name

    @pytest.mark.asyncio
    async def test_product_set_null_on_delete(self, db_session, test_tenant):
        """Test that product_id is set to NULL when product is deleted."""
        from app.models.product import Product

        # Create a deletable product
        product = Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="DELETABLE-PRODUCT",
            name="Deletable Product",
        )
        db_session.add(product)
        await db_session.commit()

        # Create run for that product
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MP-018",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            product_id=product.id,
        )
        db_session.add(run)
        await db_session.commit()

        run_id = run.id

        # Delete product
        await db_session.delete(product)
        await db_session.commit()

        # Verify run still exists but product_id is NULL
        result = await db_session.execute(select(ProductionRun).where(ProductionRun.id == run_id))
        updated_run = result.scalar_one()
        assert updated_run.product_id is None


class TestLegacyVsMultiPlateMode:
    """Tests for legacy (item-based) vs multi-plate mode detection."""

    @pytest.mark.asyncio
    async def test_legacy_mode_run(self, db_session, test_tenant, test_model):
        """Test that legacy runs (total_plates=0) work correctly."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-LEGACY-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=0,  # Legacy mode
        )
        db_session.add(run)
        await db_session.commit()

        # Add item (legacy way)
        item = ProductionRunItem(
            id=uuid4(),
            production_run_id=run.id,
            model_id=test_model.id,  # Use test_model since model_id references models table
            quantity=5,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.is_multi_plate is False
        # Query items and plates directly to avoid lazy loading issues
        items_result = await db_session.execute(
            select(ProductionRunItem).where(ProductionRunItem.production_run_id == run.id)
        )
        items = items_result.scalars().all()
        assert len(items) == 1

        plates_result = await db_session.execute(
            select(ProductionRunPlate).where(ProductionRunPlate.production_run_id == run.id)
        )
        plates = plates_result.scalars().all()
        assert len(plates) == 0

    @pytest.mark.asyncio
    async def test_multi_plate_mode_run(self, db_session, test_tenant, test_model, test_printer):
        """Test that multi-plate runs work correctly."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MULTI-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=3,  # Multi-plate mode
        )
        db_session.add(run)
        await db_session.commit()

        # Add plates (new way)
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

        assert run.is_multi_plate is True
        assert len(run.plates) == 3
        # Items can still exist (for backward compatibility) but plates is the primary

    @pytest.mark.asyncio
    async def test_mode_detection_pattern(
        self, db_session, test_tenant, test_model, test_printer, test_product
    ):
        """Test the pattern for detecting which mode to use."""

        def get_run_mode(run: ProductionRun) -> str:
            """Determine which mode a run is using."""
            if run.total_plates > 0:
                return "multi_plate"
            return "legacy"

        # Create legacy run
        legacy_run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MODE-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=0,
        )
        db_session.add(legacy_run)
        await db_session.commit()

        # Create multi-plate run
        multi_run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-MODE-002",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            total_plates=37,
        )
        db_session.add(multi_run)
        await db_session.commit()

        assert get_run_mode(legacy_run) == "legacy"
        assert get_run_mode(multi_run) == "multi_plate"
