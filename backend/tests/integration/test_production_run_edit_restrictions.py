"""
Integration Tests for Production Run Edit Restrictions

Tests the complete API behavior for editing production runs with status-based restrictions.

Scenarios Covered:
1. Editing in_progress runs (should allow all fields)
2. Editing completed runs (should only allow notes)
3. Editing failed runs (should only allow notes)
4. Editing cancelled runs (should only allow notes)
5. Editing items on immutable runs (should fail)
6. Editing materials on immutable runs (should fail)
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from httpx import AsyncClient

from app.models.production_run import ProductionRun, ProductionRunItem, ProductionRunMaterial
from app.models.spool import Spool


@pytest.mark.asyncio
class TestProductionRunEditRestrictions:
    """Tests for production run edit restrictions based on status."""

    async def test_copied_working_test(self, async_client: AsyncClient, db_session, test_tenant):
        """Copied from working test file to verify fixtures work."""
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

        response = await async_client.get("/api/v1/production-runs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5

    async def test_update_in_progress_run_all_fields(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that in_progress runs can be updated with all fields."""
        # Create production run with "in_progress" status (minimal fields like working test)
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-001",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(production_run)
        await db_session.commit()
        await db_session.refresh(production_run)

        run_id = production_run.id

        # Update multiple fields
        update_data = {
            "printer_name": "Prusa XL",
            "bed_temperature": 65,
            "nozzle_temperature": 215,
            "notes": "Updated notes",
            "quality_rating": 4,
            "quality_notes": "Good quality",
        }

        response = await async_client.patch(f"/api/v1/production-runs/{run_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["printer_name"] == "Prusa XL"
        assert data["bed_temperature"] == 65
        assert data["nozzle_temperature"] == 215
        assert data["notes"] == "Updated notes"
        assert data["quality_rating"] == 4
        assert data["quality_notes"] == "Good quality"

    async def test_update_completed_run_notes_only_succeeds(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that completed runs can only be updated with notes field."""
        # Create production run with "completed" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-002",
            started_at=datetime.now(timezone.utc) - timedelta(hours=5),
            completed_at=datetime.now(timezone.utc),
            status="completed",
        )
        db_session.add(production_run)
        await db_session.commit()
        await db_session.refresh(production_run)

        run_id = production_run.id

        # Update only notes - should succeed
        update_data = {"notes": "Added post-completion notes"}

        response = await async_client.patch(f"/api/v1/production-runs/{run_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Added post-completion notes"
        assert data["status"] == "completed"

    async def test_update_completed_run_other_fields_fails(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that completed runs cannot be updated with fields other than notes."""
        # Create production run with "completed" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-003",
            started_at=datetime.now(timezone.utc) - timedelta(hours=5),
            completed_at=datetime.now(timezone.utc),
            status="completed",
        )
        db_session.add(production_run)
        await db_session.commit()
        await db_session.refresh(production_run)

        run_id = production_run.id

        # Try to update printer_name - should fail
        update_data = {"printer_name": "Prusa XL", "bed_temperature": 65}

        response = await async_client.patch(f"/api/v1/production-runs/{run_id}", json=update_data)

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "Cannot modify" in error_detail
        assert "completed" in error_detail
        assert "Only 'notes' can be updated" in error_detail

    async def test_update_failed_run_notes_only_succeeds(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that failed runs can only be updated with notes field."""
        # Create production run with "failed" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-004",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            completed_at=datetime.now(timezone.utc),
            status="failed",
        )
        db_session.add(production_run)
        await db_session.commit()
        await db_session.refresh(production_run)

        run_id = production_run.id

        # Update only notes - should succeed
        update_data = {"notes": "Print failed due to nozzle clog"}

        response = await async_client.patch(f"/api/v1/production-runs/{run_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Print failed due to nozzle clog"
        assert data["status"] == "failed"

    async def test_update_failed_run_other_fields_fails(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that failed runs cannot be updated with fields other than notes."""
        # Create production run with "failed" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-005",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            completed_at=datetime.now(timezone.utc),
            status="failed",
        )
        db_session.add(production_run)
        await db_session.commit()
        await db_session.refresh(production_run)

        run_id = production_run.id

        # Try to update quality_rating - should fail
        update_data = {"quality_rating": 1}

        response = await async_client.patch(f"/api/v1/production-runs/{run_id}", json=update_data)

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "Cannot modify" in error_detail
        assert "failed" in error_detail

    async def test_update_cancelled_run_notes_only_succeeds(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that cancelled runs can only be updated with notes field."""
        # Create production run with "cancelled" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-006",
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            completed_at=datetime.now(timezone.utc),
            status="cancelled",
        )
        db_session.add(production_run)
        await db_session.commit()
        await db_session.refresh(production_run)

        run_id = production_run.id

        # Update only notes - should succeed
        update_data = {"notes": "Cancelled due to material change"}

        response = await async_client.patch(f"/api/v1/production-runs/{run_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Cancelled due to material change"
        assert data["status"] == "cancelled"

    async def test_update_cancelled_run_other_fields_fails(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that cancelled runs cannot be updated with fields other than notes."""
        # Create production run with "cancelled" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-007",
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            completed_at=datetime.now(timezone.utc),
            status="cancelled",
        )
        db_session.add(production_run)
        await db_session.commit()
        await db_session.refresh(production_run)

        run_id = production_run.id

        # Try to update status back to in_progress - should fail
        update_data = {"status": "in_progress"}

        response = await async_client.patch(f"/api/v1/production-runs/{run_id}", json=update_data)

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "Cannot modify" in error_detail
        assert "cancelled" in error_detail

    async def test_update_item_on_completed_run_fails(
        self, async_client: AsyncClient, db_session, test_tenant, test_model
    ):
        """Test that items cannot be updated on completed production runs."""
        # Create production run with "completed" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-008",
            started_at=datetime.now(timezone.utc) - timedelta(hours=5),
            completed_at=datetime.now(timezone.utc),
            status="completed",
        )
        db_session.add(production_run)
        await db_session.commit()

        # Create item using test_model fixture
        item = ProductionRunItem(
            production_run_id=production_run.id,
            model_id=test_model.id,
            quantity=10,
            bed_position="A1",
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        run_id = production_run.id
        item_id = item.id

        # Try to update quantity - should fail
        update_data = {"quantity": 15}

        response = await async_client.patch(
            f"/api/v1/production-runs/{run_id}/items/{item_id}", json=update_data
        )

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "Cannot modify items" in error_detail
        assert "completed" in error_detail

    async def test_update_material_on_completed_run_fails(
        self, async_client: AsyncClient, db_session, test_tenant, test_material_type
    ):
        """Test that materials cannot be updated on completed production runs."""
        # Create spool using test_material_type fixture
        spool = Spool(
            tenant_id=test_tenant.id,
            spool_id="FIL-002",
            material_type_id=test_material_type.id,
            brand="eSun",
            color="Red",
            diameter=1.75,
            initial_weight=1000,
            current_weight=600,
            purchased_quantity=1,
            purchase_date=datetime.now(timezone.utc).date(),
            purchase_price=Decimal("25.00"),
            is_active=True,
        )
        db_session.add(spool)
        await db_session.commit()

        # Create production run with "completed" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-009",
            started_at=datetime.now(timezone.utc) - timedelta(hours=5),
            completed_at=datetime.now(timezone.utc),
            status="completed",
        )
        db_session.add(production_run)
        await db_session.commit()

        # Create material
        material = ProductionRunMaterial(
            production_run_id=production_run.id,
            spool_id=spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            cost_per_gram=Decimal("0.025"),
        )
        db_session.add(material)
        await db_session.commit()
        await db_session.refresh(material)

        run_id = production_run.id
        material_id = material.id

        # Try to update weight - should fail
        update_data = {"estimated_model_weight_grams": "150.0"}

        response = await async_client.patch(
            f"/api/v1/production-runs/{run_id}/materials/{material_id}", json=update_data
        )

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "Cannot modify materials" in error_detail
        assert "completed" in error_detail

    async def test_update_item_on_in_progress_run_succeeds(
        self, async_client: AsyncClient, db_session, test_tenant, test_model
    ):
        """Test that items CAN be updated on in_progress production runs."""
        # Create production run with "in_progress" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-010",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(production_run)
        await db_session.commit()

        # Create item using test_model fixture
        item = ProductionRunItem(
            production_run_id=production_run.id,
            model_id=test_model.id,
            quantity=10,
            bed_position="A1",
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        run_id = production_run.id
        item_id = item.id

        # Update quantity - should succeed
        update_data = {"quantity": 15}

        response = await async_client.patch(
            f"/api/v1/production-runs/{run_id}/items/{item_id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 15

    async def test_update_material_on_in_progress_run_succeeds(
        self, async_client: AsyncClient, db_session, test_tenant, test_material_type
    ):
        """Test that materials CAN be updated on in_progress production runs."""
        # Create spool using test_material_type fixture
        spool = Spool(
            tenant_id=test_tenant.id,
            spool_id="FIL-003",
            material_type_id=test_material_type.id,
            brand="eSun",
            color="Green",
            diameter=1.75,
            initial_weight=1000,
            current_weight=700,
            purchased_quantity=1,
            purchase_date=datetime.now(timezone.utc).date(),
            purchase_price=Decimal("25.00"),
            is_active=True,
        )
        db_session.add(spool)
        await db_session.commit()

        # Create production run with "in_progress" status
        production_run = ProductionRun(
            tenant_id=test_tenant.id,
            run_number="TEST-RUN-011",
            started_at=datetime.now(timezone.utc),
            status="in_progress",
        )
        db_session.add(production_run)
        await db_session.commit()

        # Create material
        material = ProductionRunMaterial(
            production_run_id=production_run.id,
            spool_id=spool.id,
            estimated_model_weight_grams=Decimal("100.0"),
            cost_per_gram=Decimal("0.025"),
        )
        db_session.add(material)
        await db_session.commit()
        await db_session.refresh(material)

        run_id = production_run.id
        material_id = material.id

        # Update weight - should succeed
        update_data = {"estimated_model_weight_grams": "150.0"}

        response = await async_client.patch(
            f"/api/v1/production-runs/{run_id}/materials/{material_id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["estimated_model_weight_grams"] == "150.0"
