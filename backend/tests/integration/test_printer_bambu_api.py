"""
Integration tests for Bambu Lab printer integration API endpoints.

Tests all endpoints in /api/v1/printers/{id}/connection and /api/v1/printers/{id}/ams
including:
- Printer connection configuration CRUD
- AMS slot mapping CRUD
- Multi-tenant isolation
- Validation and error handling
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AMSSlotMapping, Printer, PrinterConnection


@pytest.mark.asyncio
class TestPrinterConnectionEndpoints:
    """Tests for printer connection configuration endpoints."""

    async def test_create_connection_bambu_lan(
        self, async_client: AsyncClient, test_printer: Printer, test_tenant
    ):
        """Test creating a Bambu LAN connection configuration."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/connection",
            json={
                "connection_type": "bambu_lan",
                "serial_number": "01P00A123456789",
                "ip_address": "192.168.1.100",
                "port": 8883,
                "access_code": "12345678",
                "ams_count": 1,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["connection_type"] == "bambu_lan"
        assert data["serial_number"] == "01P00A123456789"
        assert data["ip_address"] == "192.168.1.100"
        assert data["port"] == 8883
        assert data["ams_count"] == 1
        assert data["is_enabled"] is True
        assert data["is_connected"] is False
        # Access code should be masked
        assert "****" in data["access_code"]

    async def test_create_connection_manual(self, async_client: AsyncClient, test_printer: Printer):
        """Test creating a manual (no-sync) connection configuration."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/connection",
            json={
                "connection_type": "manual",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["connection_type"] == "manual"
        assert data["serial_number"] is None
        assert data["ams_count"] == 0

    async def test_create_connection_replaces_existing(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test that creating a new connection replaces existing one."""
        # Create initial connection
        response1 = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/connection",
            json={
                "connection_type": "manual",
            },
        )
        assert response1.status_code == 201

        # Create replacement connection
        response2 = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/connection",
            json={
                "connection_type": "bambu_lan",
                "serial_number": "01P00A123456789",
                "ip_address": "192.168.1.100",
                "access_code": "12345678",
            },
        )
        assert response2.status_code == 201
        data = response2.json()
        assert data["connection_type"] == "bambu_lan"

    async def test_create_connection_printer_not_found(self, async_client: AsyncClient):
        """Test creating connection for non-existent printer."""
        fake_id = uuid4()
        response = await async_client.post(
            f"/api/v1/printers/{fake_id}/connection",
            json={"connection_type": "manual"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_connection(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test getting printer connection configuration."""
        # Create connection first
        connection = PrinterConnection(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            connection_type="bambu_lan",
            serial_number="01P00A123456789",
            ip_address="192.168.1.100",
            access_code="12345678",
            ams_count=1,
        )
        db_session.add(connection)
        await db_session.commit()

        response = await async_client.get(f"/api/v1/printers/{test_printer.id}/connection")

        assert response.status_code == 200
        data = response.json()
        assert data["connection_type"] == "bambu_lan"
        assert data["serial_number"] == "01P00A123456789"

    async def test_get_connection_not_found(self, async_client: AsyncClient, test_printer: Printer):
        """Test getting connection when none exists."""
        response = await async_client.get(f"/api/v1/printers/{test_printer.id}/connection")

        assert response.status_code == 404
        assert "no connection" in response.json()["detail"].lower()

    async def test_update_connection(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test updating printer connection configuration."""
        # Create connection first
        connection = PrinterConnection(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            connection_type="bambu_lan",
            serial_number="01P00A123456789",
            ip_address="192.168.1.100",
            access_code="12345678",
            ams_count=1,
        )
        db_session.add(connection)
        await db_session.commit()

        response = await async_client.put(
            f"/api/v1/printers/{test_printer.id}/connection",
            json={
                "ip_address": "192.168.1.200",
                "ams_count": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ip_address"] == "192.168.1.200"
        assert data["ams_count"] == 2
        # Serial should remain unchanged
        assert data["serial_number"] == "01P00A123456789"

    async def test_delete_connection(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test deleting printer connection configuration."""
        # Create connection first
        connection = PrinterConnection(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            connection_type="manual",
        )
        db_session.add(connection)
        await db_session.commit()

        response = await async_client.delete(f"/api/v1/printers/{test_printer.id}/connection")

        assert response.status_code == 204

        # Verify deleted
        get_response = await async_client.get(f"/api/v1/printers/{test_printer.id}/connection")
        assert get_response.status_code == 404


@pytest.mark.asyncio
class TestAMSSlotMappingEndpoints:
    """Tests for AMS slot mapping endpoints."""

    async def test_list_ams_slots_empty(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test listing AMS slots when none are mapped."""
        # Create connection with AMS
        connection = PrinterConnection(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            connection_type="bambu_lan",
            ams_count=1,
        )
        db_session.add(connection)
        await db_session.commit()

        response = await async_client.get(f"/api/v1/printers/{test_printer.id}/ams")

        assert response.status_code == 200
        data = response.json()
        assert data["printer_id"] == str(test_printer.id)
        assert data["ams_count"] == 1
        assert data["total_slots"] == 4
        assert data["slots"] == []

    async def test_map_ams_slot(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        test_spool,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test mapping an AMS slot to a spool."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/ams/map",
            json={
                "ams_id": 0,
                "tray_id": 2,
                "spool_id": str(test_spool.id),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["ams_id"] == 0
        assert data["tray_id"] == 2
        assert data["spool_id"] == str(test_spool.id)
        assert data["is_auto_mapped"] is False
        assert data["absolute_slot_id"] == 2  # (0 * 4) + 2
        assert data["slot_display_name"] == "AMS 1 Slot 3"

    async def test_map_ams_slot_without_spool(
        self, async_client: AsyncClient, test_printer: Printer
    ):
        """Test creating AMS slot entry without mapping to spool."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/ams/map",
            json={
                "ams_id": 0,
                "tray_id": 0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["spool_id"] is None

    async def test_map_ams_slot_invalid_spool(
        self, async_client: AsyncClient, test_printer: Printer
    ):
        """Test mapping AMS slot to non-existent spool."""
        fake_spool_id = uuid4()
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/ams/map",
            json={
                "ams_id": 0,
                "tray_id": 0,
                "spool_id": str(fake_spool_id),
            },
        )

        assert response.status_code == 404
        assert "spool" in response.json()["detail"].lower()

    async def test_map_ams_slot_updates_existing(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        test_spool,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test that mapping same slot updates existing mapping."""
        # Create initial mapping
        mapping = AMSSlotMapping(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            ams_id=0,
            tray_id=0,
            spool_id=None,
        )
        db_session.add(mapping)
        await db_session.commit()

        # Update with spool
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/ams/map",
            json={
                "ams_id": 0,
                "tray_id": 0,
                "spool_id": str(test_spool.id),
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["spool_id"] == str(test_spool.id)

    async def test_unmap_ams_slot(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        test_spool,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test unmapping a spool from an AMS slot."""
        # Create mapping
        mapping = AMSSlotMapping(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            ams_id=0,
            tray_id=1,
            spool_id=test_spool.id,
        )
        db_session.add(mapping)
        await db_session.commit()

        response = await async_client.delete(f"/api/v1/printers/{test_printer.id}/ams/0/1")

        assert response.status_code == 204

    async def test_unmap_ams_slot_not_found(self, async_client: AsyncClient, test_printer: Printer):
        """Test unmapping non-existent slot."""
        response = await async_client.delete(f"/api/v1/printers/{test_printer.id}/ams/0/0")

        assert response.status_code == 404

    async def test_list_ams_slots_with_mappings(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        test_spool,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test listing AMS slots with spool mappings."""
        # Create connection
        connection = PrinterConnection(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            connection_type="bambu_lan",
            ams_count=1,
        )
        db_session.add(connection)

        # Create mappings
        mapping1 = AMSSlotMapping(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            ams_id=0,
            tray_id=0,
            spool_id=test_spool.id,
            last_reported_type="PLA",
            last_reported_color="FF0000FF",
            last_reported_remain=85,
            has_filament=True,
        )
        mapping2 = AMSSlotMapping(
            tenant_id=test_tenant.id,
            printer_id=test_printer.id,
            ams_id=0,
            tray_id=1,
            spool_id=None,
            has_filament=False,
        )
        db_session.add_all([mapping1, mapping2])
        await db_session.commit()

        response = await async_client.get(f"/api/v1/printers/{test_printer.id}/ams")

        assert response.status_code == 200
        data = response.json()
        assert data["ams_count"] == 1
        assert len(data["slots"]) == 2

        # Check slot with spool
        slot0 = next(s for s in data["slots"] if s["tray_id"] == 0)
        assert slot0["spool_id"] == str(test_spool.id)
        assert slot0["last_reported_type"] == "PLA"
        assert slot0["last_reported_remain"] == 85
        assert slot0["spool_summary"] is not None
        assert slot0["spool_summary"]["spool_id"] == test_spool.spool_id

        # Check empty slot
        slot1 = next(s for s in data["slots"] if s["tray_id"] == 1)
        assert slot1["spool_id"] is None
        assert slot1["spool_summary"] is None


@pytest.mark.asyncio
class TestPrinterConnectionTenantIsolation:
    """Tests for multi-tenant isolation of printer connections."""

    async def test_cannot_access_other_tenant_connection(
        self, async_client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        """Test that connections from other tenants are not accessible."""
        from app.models.tenant import Tenant

        # Create another tenant with printer and connection
        other_tenant = Tenant(id=uuid4(), name="Other Tenant", slug="other-tenant")
        db_session.add(other_tenant)
        await db_session.flush()

        other_printer = Printer(
            id=uuid4(),
            tenant_id=other_tenant.id,
            name="Other Printer",
        )
        db_session.add(other_printer)
        await db_session.flush()

        other_connection = PrinterConnection(
            tenant_id=other_tenant.id,
            printer_id=other_printer.id,
            connection_type="bambu_lan",
            serial_number="OTHER123",
        )
        db_session.add(other_connection)
        await db_session.commit()

        # Try to access it
        response = await async_client.get(f"/api/v1/printers/{other_printer.id}/connection")
        assert response.status_code == 404

    async def test_cannot_map_slot_to_other_tenant_spool(
        self,
        async_client: AsyncClient,
        test_printer: Printer,
        db_session: AsyncSession,
        test_material_type,
    ):
        """Test that you cannot map AMS slot to another tenant's spool."""
        from app.models.tenant import Tenant
        from decimal import Decimal

        # Create another tenant with spool
        other_tenant = Tenant(id=uuid4(), name="Other Tenant", slug="other-tenant")
        db_session.add(other_tenant)
        await db_session.flush()

        from app.models.spool import Spool

        other_spool = Spool(
            id=uuid4(),
            tenant_id=other_tenant.id,
            material_type_id=test_material_type.id,
            spool_id="OTHER-SPOOL",
            brand="Other Brand",
            color="Blue",
            initial_weight=1000.0,
            current_weight=500.0,
            purchase_price=Decimal("20.00"),
        )
        db_session.add(other_spool)
        await db_session.commit()

        # Try to map to other tenant's spool
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/ams/map",
            json={
                "ams_id": 0,
                "tray_id": 0,
                "spool_id": str(other_spool.id),
            },
        )

        assert response.status_code == 404
        assert "spool" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestPrinterConnectionValidation:
    """Tests for input validation on connection endpoints."""

    async def test_invalid_connection_type(self, async_client: AsyncClient, test_printer: Printer):
        """Test that invalid connection type is rejected."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/connection",
            json={"connection_type": "invalid_type"},
        )

        assert response.status_code == 422

    async def test_invalid_ams_count(self, async_client: AsyncClient, test_printer: Printer):
        """Test that AMS count > 4 is rejected."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/connection",
            json={
                "connection_type": "bambu_lan",
                "ams_count": 5,
            },
        )

        assert response.status_code == 422

    async def test_invalid_port(self, async_client: AsyncClient, test_printer: Printer):
        """Test that invalid port is rejected."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/connection",
            json={
                "connection_type": "bambu_lan",
                "port": 70000,
            },
        )

        assert response.status_code == 422

    async def test_invalid_ams_id_in_mapping(
        self, async_client: AsyncClient, test_printer: Printer
    ):
        """Test that AMS ID > 3 is rejected."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/ams/map",
            json={
                "ams_id": 4,
                "tray_id": 0,
            },
        )

        assert response.status_code == 422

    async def test_invalid_tray_id_in_mapping(
        self, async_client: AsyncClient, test_printer: Printer
    ):
        """Test that tray ID > 3 is rejected."""
        response = await async_client.post(
            f"/api/v1/printers/{test_printer.id}/ams/map",
            json={
                "ams_id": 0,
                "tray_id": 5,
            },
        )

        assert response.status_code == 422
