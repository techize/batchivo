"""
Integration tests for Printer API endpoints.

Tests all endpoints in /api/v1/printers including:
- CRUD operations
- Multi-tenant isolation
- Validation and error handling
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.printer import Printer


@pytest.mark.asyncio
class TestPrintersEndpoints:
    """Tests for printer CRUD endpoints."""

    async def test_create_printer_minimal(self, async_client: AsyncClient, test_tenant):
        """Test creating a printer with minimal data."""
        response = await async_client.post("/api/v1/printers", json={"name": "Test Printer"})

        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["tenant_id"] == str(test_tenant.id)
        assert data["name"] == "Test Printer"
        assert data["is_active"] is True

    async def test_create_printer_full(self, async_client: AsyncClient, test_tenant):
        """Test creating a printer with all fields."""
        response = await async_client.post(
            "/api/v1/printers",
            json={
                "name": "Bambu X1 Carbon",
                "manufacturer": "Bambu Lab",
                "model": "X1 Carbon",
                "serial_number": "X1C-12345",
                "bed_size_x_mm": 256,
                "bed_size_y_mm": 256,
                "bed_size_z_mm": 256,
                "nozzle_diameter_mm": "0.4",
                "default_bed_temp": 60,
                "default_nozzle_temp": 220,
                "capabilities": {"ams": True, "multi_color": True, "lidar": True},
                "notes": "Primary production printer",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Bambu X1 Carbon"
        assert data["manufacturer"] == "Bambu Lab"
        assert data["model"] == "X1 Carbon"
        assert data["bed_size_x_mm"] == 256
        assert data["capabilities"]["ams"] is True

    async def test_list_printers_empty(self, async_client: AsyncClient):
        """Test listing printers when none exist."""
        response = await async_client.get("/api/v1/printers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["printers"] == []

    async def test_list_printers_with_data(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test listing printers with pagination."""
        # Create 5 printers
        for i in range(5):
            printer = Printer(
                tenant_id=test_tenant.id,
                name=f"Printer {i}",
                manufacturer="Test Brand",
                is_active=i < 3,  # First 3 active
            )
            db_session.add(printer)
        await db_session.commit()

        # List all
        response = await async_client.get("/api/v1/printers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5

        # Filter by active
        response = await async_client.get("/api/v1/printers?is_active=true")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

        # Pagination
        response = await async_client.get("/api/v1/printers?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["printers"]) == 2
        assert data["skip"] == 2
        assert data["limit"] == 2

    async def test_get_printer(self, async_client: AsyncClient, test_printer):
        """Test getting a specific printer."""
        response = await async_client.get(f"/api/v1/printers/{test_printer.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_printer.id)
        assert data["name"] == test_printer.name

    async def test_get_printer_not_found(self, async_client: AsyncClient):
        """Test getting a non-existent printer."""
        fake_id = uuid4()
        response = await async_client.get(f"/api/v1/printers/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_update_printer(self, async_client: AsyncClient, test_printer):
        """Test updating a printer."""
        response = await async_client.put(
            f"/api/v1/printers/{test_printer.id}",
            json={"name": "Updated Printer Name", "notes": "Updated notes"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Printer Name"
        assert data["notes"] == "Updated notes"

    async def test_update_printer_not_found(self, async_client: AsyncClient):
        """Test updating a non-existent printer."""
        fake_id = uuid4()
        response = await async_client.put(f"/api/v1/printers/{fake_id}", json={"name": "New Name"})

        assert response.status_code == 404

    async def test_delete_printer(self, async_client: AsyncClient, test_printer):
        """Test deleting (soft delete) a printer."""
        response = await async_client.delete(f"/api/v1/printers/{test_printer.id}")

        assert response.status_code == 204

        # Verify soft deleted (is_active=False)
        response = await async_client.get(f"/api/v1/printers/{test_printer.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_delete_printer_not_found(self, async_client: AsyncClient):
        """Test deleting a non-existent printer."""
        fake_id = uuid4()
        response = await async_client.delete(f"/api/v1/printers/{fake_id}")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestPrintersTenantIsolation:
    """Tests for multi-tenant isolation."""

    async def test_cannot_access_other_tenant_printer(self, async_client: AsyncClient, db_session):
        """Test that printers from other tenants are not accessible."""
        # Create another tenant with a printer
        from app.models.tenant import Tenant

        other_tenant = Tenant(id=uuid4(), name="Other Tenant", slug="other-tenant")
        db_session.add(other_tenant)
        await db_session.flush()

        other_printer = Printer(id=uuid4(), tenant_id=other_tenant.id, name="Other Tenant Printer")
        db_session.add(other_printer)
        await db_session.commit()

        # Try to access it
        response = await async_client.get(f"/api/v1/printers/{other_printer.id}")
        assert response.status_code == 404

    async def test_list_only_shows_tenant_printers(
        self, async_client: AsyncClient, db_session, test_tenant
    ):
        """Test that listing only shows current tenant's printers."""
        from app.models.tenant import Tenant

        # Create printer for test tenant
        my_printer = Printer(tenant_id=test_tenant.id, name="My Printer")
        db_session.add(my_printer)

        # Create another tenant with a printer
        other_tenant = Tenant(id=uuid4(), name="Other Tenant", slug="other-tenant")
        db_session.add(other_tenant)
        await db_session.flush()

        other_printer = Printer(tenant_id=other_tenant.id, name="Other Printer")
        db_session.add(other_printer)
        await db_session.commit()

        # List should only show my printer
        response = await async_client.get("/api/v1/printers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["printers"][0]["name"] == "My Printer"
