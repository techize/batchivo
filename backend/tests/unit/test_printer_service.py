"""Unit tests for PrinterService."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.printer import PrinterCreate, PrinterUpdate
from app.services.printer_service import PrinterService


class TestPrinterServiceCreate:
    """Tests for printer creation."""

    @pytest.mark.asyncio
    async def test_create_printer_basic(self, db_session, test_tenant):
        """Test creating a basic printer."""
        service = PrinterService(db_session, test_tenant)

        data = PrinterCreate(
            name="Test Printer",
            manufacturer="Test Manufacturer",
            model="Test Model",
        )

        printer = await service.create_printer(data)

        assert printer.id is not None
        assert printer.tenant_id == test_tenant.id
        assert printer.name == "Test Printer"
        assert printer.manufacturer == "Test Manufacturer"
        assert printer.model == "Test Model"
        assert printer.is_active is True

    @pytest.mark.asyncio
    async def test_create_printer_full_details(self, db_session, test_tenant):
        """Test creating a printer with all optional fields."""
        service = PrinterService(db_session, test_tenant)

        data = PrinterCreate(
            name="Bambu A1 Mini",
            manufacturer="Bambu Lab",
            model="A1 Mini",
            serial_number="SN123456",
            bed_size_x_mm=180,
            bed_size_y_mm=180,
            bed_size_z_mm=180,
            nozzle_diameter_mm=Decimal("0.4"),
            default_bed_temp=60,
            default_nozzle_temp=220,
            capabilities={"ams": True, "multi_color": True},
            notes="Test printer notes",
        )

        printer = await service.create_printer(data)

        assert printer.name == "Bambu A1 Mini"
        assert printer.bed_size_x_mm == 180
        assert printer.bed_size_y_mm == 180
        assert printer.bed_size_z_mm == 180
        assert printer.nozzle_diameter_mm == Decimal("0.4")
        assert printer.default_bed_temp == 60
        assert printer.default_nozzle_temp == 220
        assert printer.capabilities == {"ams": True, "multi_color": True}
        assert printer.notes == "Test printer notes"

    @pytest.mark.asyncio
    async def test_create_printer_tenant_isolation(self, db_session, test_tenant):
        """Test that created printer belongs to the correct tenant."""
        service = PrinterService(db_session, test_tenant)

        data = PrinterCreate(name="Isolated Printer")
        printer = await service.create_printer(data)

        assert printer.tenant_id == test_tenant.id


class TestPrinterServiceRead:
    """Tests for printer retrieval."""

    @pytest.mark.asyncio
    async def test_get_printer_by_id(self, db_session, test_tenant, test_printer):
        """Test retrieving a printer by ID."""
        service = PrinterService(db_session, test_tenant)

        printer = await service.get_printer(test_printer.id)

        assert printer is not None
        assert printer.id == test_printer.id
        assert printer.name == test_printer.name

    @pytest.mark.asyncio
    async def test_get_printer_not_found(self, db_session, test_tenant):
        """Test retrieving a non-existent printer returns None."""
        service = PrinterService(db_session, test_tenant)

        printer = await service.get_printer(uuid4())

        assert printer is None

    @pytest.mark.asyncio
    async def test_get_printer_by_name(self, db_session, test_tenant, test_printer):
        """Test retrieving a printer by name."""
        service = PrinterService(db_session, test_tenant)

        printer = await service.get_printer_by_name(test_printer.name)

        assert printer is not None
        assert printer.id == test_printer.id

    @pytest.mark.asyncio
    async def test_get_printer_by_name_not_found(self, db_session, test_tenant):
        """Test retrieving a non-existent printer by name returns None."""
        service = PrinterService(db_session, test_tenant)

        printer = await service.get_printer_by_name("Nonexistent Printer")

        assert printer is None

    @pytest.mark.asyncio
    async def test_get_printer_tenant_isolation(self, db_session, test_tenant):
        """Test that printer retrieval respects tenant isolation."""
        service = PrinterService(db_session, test_tenant)

        # Create printer for this tenant
        data = PrinterCreate(name="Tenant Printer")
        printer = await service.create_printer(data)

        # Create another tenant
        from app.models.tenant import Tenant

        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant",
            slug="other-tenant",
        )
        db_session.add(other_tenant)
        await db_session.commit()

        # Service for other tenant shouldn't see first tenant's printer
        other_service = PrinterService(db_session, other_tenant)
        retrieved = await other_service.get_printer(printer.id)

        assert retrieved is None


class TestPrinterServiceList:
    """Tests for listing printers."""

    @pytest.mark.asyncio
    async def test_list_printers_empty(self, db_session, test_tenant):
        """Test listing printers when none exist."""
        service = PrinterService(db_session, test_tenant)

        result = await service.list_printers()

        assert result.total == 0
        assert result.printers == []

    @pytest.mark.asyncio
    async def test_list_printers_with_data(self, db_session, test_tenant):
        """Test listing printers with data."""
        service = PrinterService(db_session, test_tenant)

        # Create multiple printers
        for i in range(3):
            data = PrinterCreate(name=f"Printer {i}")
            await service.create_printer(data)

        result = await service.list_printers()

        assert result.total == 3
        assert len(result.printers) == 3

    @pytest.mark.asyncio
    async def test_list_printers_pagination(self, db_session, test_tenant):
        """Test listing printers with pagination."""
        service = PrinterService(db_session, test_tenant)

        # Create 5 printers
        for i in range(5):
            data = PrinterCreate(name=f"Printer {chr(65 + i)}")  # A, B, C, D, E
            await service.create_printer(data)

        # Get first page
        result = await service.list_printers(skip=0, limit=2)

        assert result.total == 5
        assert len(result.printers) == 2
        assert result.skip == 0
        assert result.limit == 2

        # Get second page
        result2 = await service.list_printers(skip=2, limit=2)

        assert result2.total == 5
        assert len(result2.printers) == 2
        assert result2.skip == 2

    @pytest.mark.asyncio
    async def test_list_printers_filter_active(self, db_session, test_tenant):
        """Test listing printers with active filter."""
        service = PrinterService(db_session, test_tenant)

        # Create active and inactive printers
        for i in range(3):
            data = PrinterCreate(name=f"Active Printer {i}")
            await service.create_printer(data)

        # Deactivate one printer
        data = PrinterCreate(name="Inactive Printer")
        printer = await service.create_printer(data)
        await service.delete_printer(printer.id)  # Soft delete

        # List only active
        result = await service.list_printers(is_active=True)

        assert result.total == 3
        assert all(p.is_active for p in result.printers)

        # List only inactive
        result_inactive = await service.list_printers(is_active=False)

        assert result_inactive.total == 1
        assert not result_inactive.printers[0].is_active

    @pytest.mark.asyncio
    async def test_list_printers_ordered_by_name(self, db_session, test_tenant):
        """Test that printers are ordered by name."""
        service = PrinterService(db_session, test_tenant)

        # Create printers out of order
        for name in ["Zebra", "Alpha", "Mega"]:
            data = PrinterCreate(name=name)
            await service.create_printer(data)

        result = await service.list_printers()

        names = [p.name for p in result.printers]
        assert names == ["Alpha", "Mega", "Zebra"]


class TestPrinterServiceUpdate:
    """Tests for printer updates."""

    @pytest.mark.asyncio
    async def test_update_printer_single_field(self, db_session, test_tenant, test_printer):
        """Test updating a single field."""
        service = PrinterService(db_session, test_tenant)

        update = PrinterUpdate(name="Updated Name")
        updated = await service.update_printer(test_printer.id, update)

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.manufacturer == test_printer.manufacturer  # Unchanged

    @pytest.mark.asyncio
    async def test_update_printer_multiple_fields(self, db_session, test_tenant, test_printer):
        """Test updating multiple fields."""
        service = PrinterService(db_session, test_tenant)

        update = PrinterUpdate(
            name="New Name",
            manufacturer="New Manufacturer",
            default_bed_temp=70,
        )
        updated = await service.update_printer(test_printer.id, update)

        assert updated.name == "New Name"
        assert updated.manufacturer == "New Manufacturer"
        assert updated.default_bed_temp == 70

    @pytest.mark.asyncio
    async def test_update_printer_not_found(self, db_session, test_tenant):
        """Test updating a non-existent printer returns None."""
        service = PrinterService(db_session, test_tenant)

        update = PrinterUpdate(name="New Name")
        result = await service.update_printer(uuid4(), update)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_printer_capabilities(self, db_session, test_tenant, test_printer):
        """Test updating printer capabilities."""
        service = PrinterService(db_session, test_tenant)

        new_capabilities = {"ams": True, "camera": True, "lidar": True}
        update = PrinterUpdate(capabilities=new_capabilities)
        updated = await service.update_printer(test_printer.id, update)

        assert updated.capabilities == new_capabilities


class TestPrinterServiceDelete:
    """Tests for printer deletion."""

    @pytest.mark.asyncio
    async def test_delete_printer_soft(self, db_session, test_tenant, test_printer):
        """Test soft deleting a printer."""
        service = PrinterService(db_session, test_tenant)

        result = await service.delete_printer(test_printer.id)

        assert result is True

        # Printer should still exist but be inactive
        printer = await service.get_printer(test_printer.id)
        assert printer is not None
        assert printer.is_active is False

    @pytest.mark.asyncio
    async def test_delete_printer_not_found(self, db_session, test_tenant):
        """Test deleting a non-existent printer returns False."""
        service = PrinterService(db_session, test_tenant)

        result = await service.delete_printer(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_hard_delete_printer(self, db_session, test_tenant, test_printer):
        """Test hard deleting a printer."""
        service = PrinterService(db_session, test_tenant)
        printer_id = test_printer.id

        result = await service.hard_delete_printer(printer_id)

        assert result is True

        # Printer should no longer exist
        printer = await service.get_printer(printer_id)
        assert printer is None

    @pytest.mark.asyncio
    async def test_hard_delete_printer_not_found(self, db_session, test_tenant):
        """Test hard deleting a non-existent printer returns False."""
        service = PrinterService(db_session, test_tenant)

        result = await service.hard_delete_printer(uuid4())

        assert result is False


class TestPrinterServiceActivePrinters:
    """Tests for getting active printers."""

    @pytest.mark.asyncio
    async def test_get_active_printers(self, db_session, test_tenant):
        """Test getting only active printers."""
        service = PrinterService(db_session, test_tenant)

        # Create active printers
        for i in range(3):
            data = PrinterCreate(name=f"Active {i}")
            await service.create_printer(data)

        # Create and deactivate one printer
        inactive_data = PrinterCreate(name="Inactive")
        inactive_printer = await service.create_printer(inactive_data)
        await service.delete_printer(inactive_printer.id)

        active_printers = await service.get_active_printers()

        assert len(active_printers) == 3
        assert all(p.is_active for p in active_printers)

    @pytest.mark.asyncio
    async def test_get_active_printers_empty(self, db_session, test_tenant):
        """Test getting active printers when none exist."""
        service = PrinterService(db_session, test_tenant)

        active_printers = await service.get_active_printers()

        assert active_printers == []

    @pytest.mark.asyncio
    async def test_get_active_printers_tenant_isolation(self, db_session, test_tenant):
        """Test that active printers list respects tenant isolation."""
        service = PrinterService(db_session, test_tenant)

        # Create printer for this tenant
        data = PrinterCreate(name="Tenant Printer")
        await service.create_printer(data)

        # Create another tenant with its own printer
        from app.models.tenant import Tenant

        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant",
            slug="other-tenant",
        )
        db_session.add(other_tenant)
        await db_session.commit()

        other_service = PrinterService(db_session, other_tenant)
        other_data = PrinterCreate(name="Other Tenant Printer")
        await other_service.create_printer(other_data)

        # Each tenant should only see their own printers
        first_active = await service.get_active_printers()
        other_active = await other_service.get_active_printers()

        assert len(first_active) == 1
        assert first_active[0].name == "Tenant Printer"

        assert len(other_active) == 1
        assert other_active[0].name == "Other Tenant Printer"
