"""
Integration tests for Production Run API endpoints.

Tests all endpoints in /api/v1/production-runs including:
- CRUD operations
- Items management
- Materials management
- Complete production run with inventory deduction
- Multi-tenant isolation
- Validation and error handling
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.production_run import ProductionRun, ProductionRunItem, ProductionRunMaterial
from app.models.tenant import Tenant


@pytest.mark.asyncio
class TestProductionRunsEndpoints:
    """Tests for production run CRUD endpoints."""

    async def test_create_production_run_minimal(self, async_client: AsyncClient, test_tenant):
        """Test creating a production run with minimal data."""
        response = await async_client.post(
            "/api/v1/production-runs",
            json={"started_at": datetime.now(timezone.utc).isoformat(), "status": "in_progress"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["tenant_id"] == str(test_tenant.id)
        assert data["status"] == "in_progress"
        assert data["run_number"] is not None  # Auto-generated

    async def test_create_production_run_full(self, async_client: AsyncClient):
        """Test creating a production run with all fields."""
        started_at = datetime.now(timezone.utc)

        response = await async_client.post(
            "/api/v1/production-runs",
            json={
                "run_number": "TEST-20250113-001",
                "started_at": started_at.isoformat(),
                "estimated_print_time_hours": 4.5,
                "estimated_total_weight_grams": 150.0,
                "estimated_tower_grams": 10.0,
                "slicer_software": "PrusaSlicer 2.7",
                "printer_name": "Prusa i3 MK3S+",
                "bed_temperature": 60,
                "nozzle_temperature": 215,
                "status": "in_progress",
                "notes": "Test print for new spool",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["run_number"] == "TEST-20250113-001"
        assert data["printer_name"] == "Prusa i3 MK3S+"
        assert Decimal(data["estimated_print_time_hours"]) == Decimal("4.5")

    async def test_list_production_runs_empty(self, async_client: AsyncClient):
        """Test listing production runs when none exist."""
        response = await async_client.get("/api/v1/production-runs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["runs"] == []
        assert data["skip"] == 0
        assert data["limit"] == 100

    async def test_list_production_runs_with_data(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test listing production runs with pagination."""
        # Create 5 production runs
        for i in range(5):
            run = ProductionRun(
                tenant_id=test_tenant.id,
                run_number=f"TEST-{i:03d}",
                started_at=datetime.now(timezone.utc) - timedelta(hours=i),
                status="completed" if i < 3 else "in_progress",
            )
            db_session.add(run)
        await db_session.commit()

        # Test default pagination
        response = await async_client.get("/api/v1/production-runs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["runs"]) == 5

        # Test with limit
        response = await async_client.get("/api/v1/production-runs?limit=2")
        data = response.json()
        assert data["total"] == 5
        assert len(data["runs"]) == 2

        # Test with skip
        response = await async_client.get("/api/v1/production-runs?skip=2&limit=2")
        data = response.json()
        assert len(data["runs"]) == 2

    async def test_list_production_runs_filter_by_status(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test filtering production runs by status."""
        # Create runs with different statuses
        for status in ["completed", "in_progress", "failed", "completed"]:
            run = ProductionRun(
                tenant_id=test_tenant.id,
                run_number=f"TEST-{status}-{uuid4().hex[:4]}",
                started_at=datetime.now(timezone.utc),
                status=status,
            )
            db_session.add(run)
        await db_session.commit()

        # Filter by completed
        response = await async_client.get("/api/v1/production-runs?status_filter=completed")
        data = response.json()
        assert data["total"] == 2
        assert all(run["status"] == "completed" for run in data["runs"])

        # Filter by in_progress
        response = await async_client.get("/api/v1/production-runs?status_filter=in_progress")
        data = response.json()
        assert data["total"] == 1

    async def test_get_production_run_by_id(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test getting a single production run by ID."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-GET-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            printer_name="Test Printer",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.get(f"/api/v1/production-runs/{run.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(run.id)
        assert data["run_number"] == "TEST-GET-001"
        assert data["printer_name"] == "Test Printer"

    async def test_get_production_run_not_found(self, async_client: AsyncClient):
        """Test getting a non-existent production run."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/v1/production-runs/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_update_production_run(self, async_client: AsyncClient, db_session, test_tenant):
        """Test updating a production run."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-UPDATE-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.patch(
            f"/api/v1/production-runs/{run.id}",
            json={
                "quality_rating": 5,
                "quality_notes": "Excellent quality!",
                "status": "completed",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quality_rating"] == 5
        assert data["quality_notes"] == "Excellent quality!"
        assert data["status"] == "completed"

    async def test_update_production_run_auto_calculate_duration(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that updating completed_at auto-calculates duration."""
        started = datetime.now(timezone.utc)
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-DURATION-001",
            started_at=started,
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        completed = started + timedelta(hours=4, minutes=30)

        response = await async_client.patch(
            f"/api/v1/production-runs/{run.id}",
            json={"completed_at": completed.isoformat(), "status": "completed"},
        )

        assert response.status_code == 200
        data = response.json()
        # Duration should be 4.5 hours
        assert abs(Decimal(data["duration_hours"]) - Decimal("4.5")) < Decimal("0.01")

    async def test_delete_production_run(self, async_client: AsyncClient, db_session, test_tenant):
        """Test deleting a production run."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-DELETE-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.delete(f"/api/v1/production-runs/{run.id}")

        assert response.status_code == 204

        # Verify deletion
        result = await db_session.execute(select(ProductionRun).where(ProductionRun.id == run.id))
        assert result.scalar_one_or_none() is None

    async def test_delete_completed_run_fails(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that deleting a completed run is prevented."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-DELETE-COMPLETED",
            started_at=datetime.now(timezone.utc),
            status="completed",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.delete(f"/api/v1/production-runs/{run.id}")

        assert response.status_code == 400
        assert "cannot delete completed" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestProductionRunItemsEndpoints:
    """Tests for production run items endpoints."""

    async def test_add_item_to_run(
        self, async_client: AsyncClient, db_session, test_tenant, test_model
    ):
        """Test adding an item to a production run."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-ITEMS-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.post(
            f"/api/v1/production-runs/{run.id}/items",
            json={
                "model_id": str(test_model.id),
                "quantity": 10,
                "bed_position": "front-left",
                "estimated_total_cost": 50.00,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["model_id"] == str(test_model.id)
        assert data["quantity"] == 10
        assert data["bed_position"] == "front-left"

    async def test_add_item_with_invalid_product_id(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test adding an item with non-existent model ID."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-INVALID-MODEL",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        fake_model_id = uuid4()

        response = await async_client.post(
            f"/api/v1/production-runs/{run.id}/items",
            json={"model_id": str(fake_model_id), "quantity": 5},
        )

        assert response.status_code == 404
        assert "model" in response.json()["detail"].lower()

    async def test_update_item(
        self, async_client: AsyncClient, db_session, test_tenant, test_model
    ):
        """Test updating a production run item."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-UPDATE-ITEM",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.flush()

        item = ProductionRunItem(
            production_run_id=run.id,
            model_id=test_model.id,
            quantity=10,
            successful_quantity=0,
            failed_quantity=0,
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        response = await async_client.patch(
            f"/api/v1/production-runs/{run.id}/items/{item.id}",
            json={"successful_quantity": 9, "failed_quantity": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["successful_quantity"] == 9
        assert data["failed_quantity"] == 1

    async def test_delete_item(
        self, async_client: AsyncClient, db_session, test_tenant, test_model
    ):
        """Test deleting a production run item."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-DELETE-ITEM",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.flush()

        item = ProductionRunItem(production_run_id=run.id, model_id=test_model.id, quantity=5)
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        response = await async_client.delete(f"/api/v1/production-runs/{run.id}/items/{item.id}")

        assert response.status_code == 204


@pytest.mark.asyncio
class TestProductionRunMaterialsEndpoints:
    """Tests for production run materials endpoints."""

    async def test_add_material_to_run(
        self, async_client: AsyncClient, db_session, test_tenant, test_spool
    ):
        """Test adding a material/spool to a production run."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-MATERIALS-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.post(
            f"/api/v1/production-runs/{run.id}/materials",
            json={
                "spool_id": str(test_spool.id),
                "estimated_model_weight_grams": 150.0,
                "estimated_flushed_grams": 10.0,
                "cost_per_gram": 0.025,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["spool_id"] == str(test_spool.id)
        assert Decimal(data["estimated_model_weight_grams"]) == Decimal("150.0")
        assert Decimal(data["cost_per_gram"]) == Decimal("0.025")

    async def test_add_material_insufficient_inventory(
        self, async_client: AsyncClient, db_session, test_tenant, test_spool
    ):
        """Test adding material when spool has insufficient inventory."""
        # Set spool weight to a low value
        test_spool.current_weight = 50.0
        db_session.add(test_spool)
        await db_session.commit()

        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-INSUFFICIENT",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        # Try to add material requiring more than available
        response = await async_client.post(
            f"/api/v1/production-runs/{run.id}/materials",
            json={
                "spool_id": str(test_spool.id),
                "estimated_model_weight_grams": 100.0,
                "estimated_flushed_grams": 10.0,
                "cost_per_gram": 0.025,
            },
        )

        assert response.status_code == 400
        assert "insufficient inventory" in response.json()["detail"].lower()

    async def test_update_material_with_spool_weighing(
        self, async_client: AsyncClient, db_session, test_tenant, test_spool
    ):
        """Test updating material with before/after spool weights."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-WEIGHING",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.flush()

        material = ProductionRunMaterial(
            production_run_id=run.id,
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            cost_per_gram=Decimal("0.025"),
        )
        db_session.add(material)
        await db_session.commit()
        await db_session.refresh(material)

        response = await async_client.patch(
            f"/api/v1/production-runs/{run.id}/materials/{material.id}",
            json={"spool_weight_before_grams": 850.0, "spool_weight_after_grams": 745.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["spool_weight_before_grams"]) == Decimal("850.0")
        assert Decimal(data["spool_weight_after_grams"]) == Decimal("745.0")
        # Actual weight should be computed: 850 - 745 = 105
        assert Decimal(data["actual_weight_from_weighing"]) == Decimal("105.0")

    async def test_delete_material(
        self, async_client: AsyncClient, db_session, test_tenant, test_spool
    ):
        """Test deleting a production run material."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-DELETE-MATERIAL",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.flush()

        material = ProductionRunMaterial(
            production_run_id=run.id,
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("50.0"),
            estimated_flushed_grams=Decimal("5.0"),
            cost_per_gram=Decimal("0.020"),
        )
        db_session.add(material)
        await db_session.commit()
        await db_session.refresh(material)

        response = await async_client.delete(
            f"/api/v1/production-runs/{run.id}/materials/{material.id}"
        )

        assert response.status_code == 204


@pytest.mark.asyncio
class TestProductionRunCompletion:
    """Tests for production run completion and inventory deduction."""

    async def test_complete_production_run_success(
        self, async_client: AsyncClient, db_session, test_tenant, test_spool
    ):
        """Test successfully completing a production run and deducting inventory."""
        initial_weight = test_spool.current_weight

        # Create run with material
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-COMPLETE-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.flush()

        material = ProductionRunMaterial(
            production_run_id=run.id,
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            actual_model_weight_grams=Decimal("105.0"),  # Actual usage recorded
            cost_per_gram=Decimal("0.025"),
        )
        db_session.add(material)
        await db_session.commit()
        await db_session.refresh(run)

        # Complete the run
        response = await async_client.post(f"/api/v1/production-runs/{run.id}/complete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
        assert data["duration_hours"] is not None

        # Verify inventory was deducted
        await db_session.refresh(test_spool)
        expected_weight = float(Decimal(str(initial_weight)) - Decimal("105.0"))
        assert abs(float(test_spool.current_weight) - expected_weight) < 0.01

    async def test_complete_without_actual_usage_fails(
        self, async_client: AsyncClient, db_session, test_tenant, test_spool
    ):
        """Test that completing without recorded actual usage fails."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-NO-ACTUAL",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.flush()

        # Material without actual usage recorded
        material = ProductionRunMaterial(
            production_run_id=run.id,
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            cost_per_gram=Decimal("0.025"),
            # No actual_weight_manual or spool_weight_before/after
        )
        db_session.add(material)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.post(f"/api/v1/production-runs/{run.id}/complete")

        assert response.status_code == 400
        assert "actual usage" in response.json()["detail"].lower()

    async def test_complete_already_completed_run_fails(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that completing an already completed run fails."""
        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-ALREADY-COMPLETE",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status="completed",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.post(f"/api/v1/production-runs/{run.id}/complete")

        assert response.status_code == 400
        assert "already completed" in response.json()["detail"].lower()

    async def test_complete_insufficient_inventory_fails(
        self, async_client: AsyncClient, db_session, test_tenant, test_spool
    ):
        """Test that completing with insufficient inventory fails."""
        # Set spool to low weight
        test_spool.current_weight = 50.0
        db_session.add(test_spool)
        await db_session.commit()

        run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-INSUFFICIENT-COMPLETE",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.flush()

        material = ProductionRunMaterial(
            production_run_id=run.id,
            spool_id=test_spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            estimated_flushed_grams=Decimal("10.0"),
            actual_model_weight_grams=Decimal("100.0"),  # More than available
            cost_per_gram=Decimal("0.025"),
        )
        db_session.add(material)
        await db_session.commit()
        await db_session.refresh(run)

        response = await async_client.post(f"/api/v1/production-runs/{run.id}/complete")

        assert response.status_code == 400
        assert "insufficient inventory" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """Tests for multi-tenant data isolation."""

    async def test_cannot_access_other_tenant_run(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that accessing another tenant's run returns 404."""
        # Create a run for a different tenant
        other_tenant = Tenant(name="Other Tenant", slug="other-tenant")
        db_session.add(other_tenant)
        await db_session.flush()

        run = ProductionRun(
            tenant_id=other_tenant.id,
            run_number="OTHER-TENANT-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        # Try to access with current tenant (test_tenant)
        response = await async_client.get(f"/api/v1/production-runs/{run.id}")

        assert response.status_code == 404

    async def test_list_only_shows_own_tenant_runs(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that list endpoint only returns current tenant's runs."""
        # Create runs for current tenant
        for i in range(3):
            run = ProductionRun(
                tenant_id=test_tenant.id,
                run_number=f"TENANT1-{i:03d}",
                started_at=datetime.now(timezone.utc),
                status="in_progress",
            )
            db_session.add(run)

        # Create runs for other tenant
        other_tenant = Tenant(name="Other Tenant", slug="other-tenant")
        db_session.add(other_tenant)
        await db_session.flush()

        for i in range(2):
            run = ProductionRun(
                tenant_id=other_tenant.id,
                run_number=f"TENANT2-{i:03d}",
                started_at=datetime.now(timezone.utc),
                status="in_progress",
            )
            db_session.add(run)

        await db_session.commit()

        # List should only show current tenant's runs
        response = await async_client.get("/api/v1/production-runs")
        data = response.json()

        assert data["total"] == 3
        assert all(run["tenant_id"] == str(test_tenant.id) for run in data["runs"])


@pytest.mark.asyncio
class TestValidation:
    """Tests for input validation."""

    async def test_create_with_invalid_status(self, async_client: AsyncClient):
        """Test creating a run with invalid status value."""
        response = await async_client.post(
            "/api/v1/production-runs",
            json={"started_at": datetime.now(timezone.utc).isoformat(), "status": "invalid_status"},
        )

        assert response.status_code == 422  # Validation error

    async def test_create_with_negative_values(self, async_client: AsyncClient):
        """Test creating a run with negative numeric values."""
        response = await async_client.post(
            "/api/v1/production-runs",
            json={
                "started_at": datetime.now(timezone.utc).isoformat(),
                "estimated_print_time_hours": -1.0,
                "status": "in_progress",
            },
        )

        assert response.status_code == 422

    async def test_create_with_completed_before_started(self, async_client: AsyncClient):
        """Test creating a run where completed_at is before started_at."""
        started = datetime.now(timezone.utc)
        completed = started - timedelta(hours=1)

        response = await async_client.post(
            "/api/v1/production-runs",
            json={
                "started_at": started.isoformat(),
                "completed_at": completed.isoformat(),
                "status": "completed",
            },
        )

        assert response.status_code == 422
