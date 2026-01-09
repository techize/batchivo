"""Unit tests for Printer model."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.printer import Printer
from app.models.tenant import Tenant


class TestPrinterModel:
    """Tests for Printer model creation and properties."""

    @pytest.mark.asyncio
    async def test_create_printer_basic(self, db_session, test_tenant):
        """Test creating a basic printer with required fields only."""
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Test Printer",
            is_active=True,
        )
        db_session.add(printer)
        await db_session.commit()
        await db_session.refresh(printer)

        assert printer.id is not None
        assert printer.tenant_id == test_tenant.id
        assert printer.name == "Test Printer"
        assert printer.is_active is True
        assert printer.created_at is not None
        assert printer.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_printer_all_fields(self, db_session, test_tenant):
        """Test creating a printer with all fields populated."""
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Bambu A1 Mini",
            manufacturer="Bambu Lab",
            model="A1 Mini",
            bed_size_x_mm=180,
            bed_size_y_mm=180,
            bed_size_z_mm=180,
            nozzle_diameter_mm=Decimal("0.4"),
            default_bed_temp=60,
            default_nozzle_temp=220,
            capabilities={"ams": True, "multi_color": True, "max_colors": 4},
            is_active=True,
            notes="Test printer for dragon prints",
        )
        db_session.add(printer)
        await db_session.commit()
        await db_session.refresh(printer)

        assert printer.name == "Bambu A1 Mini"
        assert printer.manufacturer == "Bambu Lab"
        assert printer.model == "A1 Mini"
        assert printer.bed_size_x_mm == 180
        assert printer.bed_size_y_mm == 180
        assert printer.bed_size_z_mm == 180
        assert printer.nozzle_diameter_mm == Decimal("0.4")
        assert printer.default_bed_temp == 60
        assert printer.default_nozzle_temp == 220
        assert printer.capabilities["ams"] is True
        assert printer.capabilities["max_colors"] == 4
        assert printer.notes == "Test printer for dragon prints"

    @pytest.mark.asyncio
    async def test_printer_default_values(self, db_session, test_tenant):
        """Test that default values are set correctly."""
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Default Test Printer",
        )
        db_session.add(printer)
        await db_session.commit()
        await db_session.refresh(printer)

        # Check defaults
        assert printer.is_active is True
        assert printer.nozzle_diameter_mm == Decimal("0.4")
        assert printer.capabilities == {} or printer.capabilities is None

    @pytest.mark.asyncio
    async def test_printer_bed_size_str_property(self, db_session, test_tenant):
        """Test the bed_size_str computed property."""
        # With all dimensions
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Full Size Printer",
            bed_size_x_mm=256,
            bed_size_y_mm=256,
            bed_size_z_mm=256,
        )

        assert printer.bed_size_str == "256x256x256"

        # With missing dimensions
        printer_partial = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Partial Printer",
            bed_size_x_mm=180,
            bed_size_y_mm=180,
        )

        assert printer_partial.bed_size_str is None

        # With no dimensions
        printer_none = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="No Size Printer",
        )

        assert printer_none.bed_size_str is None

    @pytest.mark.asyncio
    async def test_printer_repr(self, db_session, test_tenant):
        """Test the __repr__ method."""
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Test Repr Printer",
            manufacturer="Test Mfg",
        )

        repr_str = repr(printer)
        assert "Test Repr Printer" in repr_str
        assert "Test Mfg" in repr_str


class TestPrinterConstraints:
    """Tests for Printer model constraints."""

    @pytest.mark.asyncio
    async def test_unique_name_per_tenant(self, db_session, test_tenant):
        """Test that printer names must be unique per tenant."""
        printer1 = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Duplicate Name",
        )
        db_session.add(printer1)
        await db_session.commit()

        # Try to create another printer with same name
        printer2 = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Duplicate Name",
        )
        db_session.add(printer2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_same_name_different_tenants(self, db_session, test_tenant):
        """Test that same printer name can exist in different tenants."""
        # Create second tenant
        tenant2 = Tenant(
            id=uuid4(),
            name="Second Tenant",
            slug="second-tenant",
            settings={},
        )
        db_session.add(tenant2)
        await db_session.commit()

        # Create printer in first tenant
        printer1 = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Shared Name Printer",
        )
        db_session.add(printer1)
        await db_session.commit()

        # Create printer with same name in second tenant - should succeed
        printer2 = Printer(
            id=uuid4(),
            tenant_id=tenant2.id,
            name="Shared Name Printer",
        )
        db_session.add(printer2)
        await db_session.commit()

        assert printer1.id != printer2.id
        assert printer1.name == printer2.name
        assert printer1.tenant_id != printer2.tenant_id

    @pytest.mark.asyncio
    async def test_tenant_cascade_delete(self, db_session):
        """Test that printers are deleted when tenant is deleted."""
        # Create tenant
        tenant = Tenant(
            id=uuid4(),
            name="Deletable Tenant",
            slug="deletable-tenant",
            settings={},
        )
        db_session.add(tenant)
        await db_session.commit()

        # Create printer
        printer = Printer(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Will Be Deleted",
        )
        db_session.add(printer)
        await db_session.commit()

        printer_id = printer.id

        # Delete tenant
        await db_session.delete(tenant)
        await db_session.commit()

        # Verify printer is deleted
        result = await db_session.execute(select(Printer).where(Printer.id == printer_id))
        deleted_printer = result.scalar_one_or_none()
        assert deleted_printer is None


class TestPrinterRelationships:
    """Tests for Printer model relationships."""

    @pytest.mark.asyncio
    async def test_printer_tenant_relationship(self, db_session, test_tenant):
        """Test the tenant relationship."""
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Relationship Test Printer",
        )
        db_session.add(printer)
        await db_session.commit()
        await db_session.refresh(printer)

        # Access tenant through relationship
        assert printer.tenant is not None
        assert printer.tenant.id == test_tenant.id
        assert printer.tenant.name == test_tenant.name

    @pytest.mark.asyncio
    async def test_tenant_printers_relationship(self, db_session, test_tenant):
        """Test accessing printers from tenant."""
        # Create multiple printers
        for i in range(3):
            printer = Printer(
                id=uuid4(),
                tenant_id=test_tenant.id,
                name=f"Test Printer {i}",
            )
            db_session.add(printer)

        await db_session.commit()

        # Query printers through the relationship by querying directly
        result = await db_session.execute(
            select(Printer).where(Printer.tenant_id == test_tenant.id)
        )
        printers = result.scalars().all()
        assert len(printers) == 3

    @pytest.mark.asyncio
    async def test_printer_model_configs_relationship(self, db_session, test_tenant, test_model):
        """Test the model_printer_configs relationship."""
        from app.models.model_printer_config import ModelPrinterConfig

        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Config Test Printer",
        )
        db_session.add(printer)
        await db_session.commit()

        # Create a config
        config = ModelPrinterConfig(
            id=uuid4(),
            model_id=test_model.id,
            printer_id=printer.id,
            prints_per_plate=4,
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(printer)

        # Access configs through relationship
        assert len(printer.model_printer_configs) == 1
        assert printer.model_printer_configs[0].prints_per_plate == 4


class TestPrinterCapabilities:
    """Tests for printer capabilities JSONB field."""

    @pytest.mark.asyncio
    async def test_capabilities_jsonb_storage(self, db_session, test_tenant):
        """Test storing complex capabilities in JSONB field."""
        capabilities = {
            "ams": True,
            "multi_color": True,
            "max_colors": 4,
            "materials": ["PLA", "PETG", "TPU"],
            "features": {
                "auto_leveling": True,
                "filament_detection": True,
                "power_loss_recovery": True,
            },
        }

        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Capable Printer",
            capabilities=capabilities,
        )
        db_session.add(printer)
        await db_session.commit()
        await db_session.refresh(printer)

        # Verify JSONB stored and retrieved correctly
        assert printer.capabilities["ams"] is True
        assert printer.capabilities["max_colors"] == 4
        assert "PLA" in printer.capabilities["materials"]
        assert printer.capabilities["features"]["auto_leveling"] is True

    @pytest.mark.asyncio
    async def test_capabilities_update(self, db_session, test_tenant):
        """Test updating capabilities."""
        printer = Printer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Updateable Printer",
            capabilities={"ams": False},
        )
        db_session.add(printer)
        await db_session.commit()

        # Update capabilities
        printer.capabilities = {"ams": True, "upgraded": True}
        await db_session.commit()
        await db_session.refresh(printer)

        assert printer.capabilities["ams"] is True
        assert printer.capabilities["upgraded"] is True
