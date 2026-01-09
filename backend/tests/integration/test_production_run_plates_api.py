"""
Integration tests for Production Run Plate API endpoints.

Tests all plate endpoints in /api/v1/production-runs/{run_id}/plates including:
- CRUD operations
- Status transitions (start, complete, fail, cancel)
- Multi-tenant isolation
- Validation and error handling
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.production_run import ProductionRun
from app.models.production_run_plate import ProductionRunPlate


@pytest.mark.asyncio
class TestProductionRunPlatesEndpoints:
    """Tests for production run plate CRUD endpoints."""

    @pytest.fixture
    async def test_production_run(self, db_session, test_tenant):
        """Create a test production run for plate tests."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)
        return run

    async def test_create_plate(
        self, async_client: AsyncClient, test_production_run, test_model, test_printer
    ):
        """Test creating a plate within a production run."""
        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates",
            json={
                "model_id": str(test_model.id),
                "printer_id": str(test_printer.id),
                "plate_number": 1,
                "plate_name": "Test Plate 1",
                "prints_per_plate": 3,
                "print_time_minutes": 45,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["production_run_id"] == str(test_production_run.id)
        assert data["model_id"] == str(test_model.id)
        assert data["printer_id"] == str(test_printer.id)
        assert data["plate_number"] == 1
        assert data["status"] == "pending"

    async def test_create_plate_with_optional_fields(
        self, async_client: AsyncClient, test_production_run, test_model, test_printer
    ):
        """Test creating a plate with all optional fields."""
        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates",
            json={
                "model_id": str(test_model.id),
                "printer_id": str(test_printer.id),
                "plate_number": 1,
                "plate_name": "Batch A - Plate 1",
                "prints_per_plate": 5,
                "print_time_minutes": 60,
                "notes": "First plate of batch A",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["plate_name"] == "Batch A - Plate 1"
        assert data["prints_per_plate"] == 5
        assert data["notes"] == "First plate of batch A"

    async def test_create_plate_invalid_run(
        self, async_client: AsyncClient, test_model, test_printer
    ):
        """Test creating a plate for non-existent run."""
        fake_run_id = uuid4()
        response = await async_client.post(
            f"/api/v1/production-runs/{fake_run_id}/plates",
            json={
                "model_id": str(test_model.id),
                "printer_id": str(test_printer.id),
                "plate_number": 1,
                "plate_name": "Test Plate",
                "prints_per_plate": 3,
            },
        )

        # API returns 400 Bad Request when production run not found
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    async def test_list_plates(
        self, async_client: AsyncClient, db_session, test_production_run, test_model, test_printer
    ):
        """Test listing plates for a production run."""
        # Create 3 plates
        for i in range(3):
            plate = ProductionRunPlate(
                production_run_id=test_production_run.id,
                model_id=test_model.id,
                printer_id=test_printer.id,
                plate_number=i + 1,
                plate_name=f"Plate {i + 1}",
                prints_per_plate=3,
                status="pending" if i == 0 else "complete",
            )
            db_session.add(plate)
        await db_session.commit()

        # List all
        response = await async_client.get(
            f"/api/v1/production-runs/{test_production_run.id}/plates"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["plates"]) == 3

        # Filter by status
        response = await async_client.get(
            f"/api/v1/production-runs/{test_production_run.id}/plates?status_filter=complete"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    async def test_get_plate(
        self, async_client: AsyncClient, db_session, test_production_run, test_model, test_printer
    ):
        """Test getting a specific plate."""
        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=test_production_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Test Plate 1",
            prints_per_plate=3,
        )
        db_session.add(plate)
        await db_session.commit()

        response = await async_client.get(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{plate.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(plate.id)
        assert data["plate_number"] == 1

    async def test_get_plate_not_found(self, async_client: AsyncClient, test_production_run):
        """Test getting a non-existent plate."""
        fake_id = uuid4()
        response = await async_client.get(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{fake_id}"
        )

        assert response.status_code == 404

    async def test_update_plate(
        self, async_client: AsyncClient, db_session, test_production_run, test_model, test_printer
    ):
        """Test updating a plate."""
        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=test_production_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Test Plate 1",
            prints_per_plate=3,
        )
        db_session.add(plate)
        await db_session.commit()

        response = await async_client.patch(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{plate.id}",
            json={"notes": "Updated notes", "successful_prints": 3, "failed_prints": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Updated notes"
        assert data["successful_prints"] == 3
        assert data["failed_prints"] == 1

    async def test_delete_plate(
        self, async_client: AsyncClient, db_session, test_production_run, test_model, test_printer
    ):
        """Test deleting a plate."""
        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=test_production_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Test Plate 1",
            prints_per_plate=3,
        )
        db_session.add(plate)
        await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{plate.id}"
        )

        assert response.status_code == 204

        # Verify deleted
        response = await async_client.get(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{plate.id}"
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestPlateStatusTransitions:
    """Tests for plate status transitions."""

    @pytest.fixture
    async def test_production_run(self, db_session, test_tenant):
        """Create a test production run for plate tests."""
        run = ProductionRun(
            id=uuid4(),
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)
        return run

    @pytest.fixture
    async def pending_plate(self, db_session, test_production_run, test_model, test_printer):
        """Create a pending plate for transition tests."""
        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=test_production_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Pending Test Plate",
            prints_per_plate=3,
            status="pending",
        )
        db_session.add(plate)
        await db_session.commit()
        await db_session.refresh(plate)
        return plate

    async def test_start_plate(self, async_client: AsyncClient, test_production_run, pending_plate):
        """Test starting a plate (pending -> printing)."""
        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{pending_plate.id}/start"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "printing"
        assert data["started_at"] is not None

    async def test_start_plate_invalid_status(
        self, async_client: AsyncClient, db_session, test_production_run, test_model, test_printer
    ):
        """Test starting a plate that's not in pending status."""
        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=test_production_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Completed Plate",
            prints_per_plate=3,
            status="complete",
        )
        db_session.add(plate)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{plate.id}/start"
        )

        assert response.status_code == 400
        assert "cannot start" in response.json()["detail"].lower()

    async def test_complete_plate(
        self, async_client: AsyncClient, test_production_run, pending_plate
    ):
        """Test completing a plate with results."""
        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{pending_plate.id}/complete",
            json={"successful_prints": 3, "failed_prints": 0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"
        assert data["successful_prints"] == 3
        assert data["failed_prints"] == 0
        assert data["completed_at"] is not None

    async def test_complete_plate_from_printing(
        self, async_client: AsyncClient, db_session, test_production_run, test_model, test_printer
    ):
        """Test completing a plate that's in printing status."""
        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=test_production_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Printing Plate",
            prints_per_plate=3,
            status="printing",
        )
        db_session.add(plate)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{plate.id}/complete",
            json={"successful_prints": 2, "failed_prints": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "complete"

    async def test_fail_plate(self, async_client: AsyncClient, test_production_run, pending_plate):
        """Test marking a plate as failed."""
        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{pending_plate.id}/fail?notes=Nozzle%20clog"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["notes"] == "Nozzle clog"

    async def test_fail_plate_already_complete(
        self, async_client: AsyncClient, db_session, test_production_run, test_model, test_printer
    ):
        """Test failing a plate that's already complete."""
        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=test_production_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Completed Plate",
            prints_per_plate=3,
            status="complete",
        )
        db_session.add(plate)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{plate.id}/fail"
        )

        assert response.status_code == 400
        assert "cannot fail" in response.json()["detail"].lower()

    async def test_cancel_plate(
        self, async_client: AsyncClient, test_production_run, pending_plate
    ):
        """Test cancelling a plate."""
        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{pending_plate.id}/cancel?notes=No%20longer%20needed"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["notes"] == "No longer needed"

    async def test_cancel_plate_already_complete(
        self, async_client: AsyncClient, db_session, test_production_run, test_model, test_printer
    ):
        """Test cancelling a plate that's already complete."""
        plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=test_production_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Completed Plate",
            prints_per_plate=3,
            status="complete",
        )
        db_session.add(plate)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/production-runs/{test_production_run.id}/plates/{plate.id}/cancel"
        )

        assert response.status_code == 400
        assert "cannot cancel" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestPlatesTenantIsolation:
    """Tests for multi-tenant isolation of plates."""

    async def test_cannot_access_other_tenant_plate(
        self, async_client: AsyncClient, db_session, test_model, test_printer
    ):
        """Test that plates from other tenants are not accessible."""
        from app.models.tenant import Tenant

        # Create another tenant with a production run and plate
        other_tenant = Tenant(id=uuid4(), name="Other Tenant", slug="other-tenant")
        db_session.add(other_tenant)
        await db_session.flush()

        other_run = ProductionRun(
            id=uuid4(),
            tenant_id=other_tenant.id,
            run_number="OTHER-RUN-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(other_run)
        await db_session.flush()

        other_plate = ProductionRunPlate(
            id=uuid4(),
            production_run_id=other_run.id,
            model_id=test_model.id,
            printer_id=test_printer.id,
            plate_number=1,
            plate_name="Other Tenant Plate",
            prints_per_plate=3,
        )
        db_session.add(other_plate)
        await db_session.commit()

        # Try to access the other tenant's plate
        response = await async_client.get(
            f"/api/v1/production-runs/{other_run.id}/plates/{other_plate.id}"
        )
        assert response.status_code == 404
