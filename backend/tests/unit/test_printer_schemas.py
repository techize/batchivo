"""Unit tests for Printer Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.printer import (
    PrinterBase,
    PrinterCreate,
    PrinterUpdate,
    PrinterResponse,
    PrinterSummary,
    PrinterListResponse,
)


class TestPrinterBase:
    """Tests for PrinterBase schema."""

    def test_printer_base_valid_minimal(self):
        """Test creating PrinterBase with only required fields."""
        data = {"name": "Bambu A1 Mini"}
        printer = PrinterBase(**data)
        assert printer.name == "Bambu A1 Mini"
        assert printer.manufacturer is None
        assert printer.model is None
        assert printer.is_active is True  # Default
        assert printer.nozzle_diameter_mm == Decimal("0.4")  # Default

    def test_printer_base_valid_full(self):
        """Test creating PrinterBase with all fields."""
        data = {
            "name": "Bambu A1 Mini",
            "manufacturer": "Bambu Lab",
            "model": "A1 Mini",
            "bed_size_x_mm": 180,
            "bed_size_y_mm": 180,
            "bed_size_z_mm": 180,
            "nozzle_diameter_mm": Decimal("0.4"),
            "default_bed_temp": 60,
            "default_nozzle_temp": 220,
            "capabilities": {"ams": True, "multi_color": True},
            "is_active": True,
            "notes": "Primary printer",
        }
        printer = PrinterBase(**data)
        assert printer.name == "Bambu A1 Mini"
        assert printer.manufacturer == "Bambu Lab"
        assert printer.model == "A1 Mini"
        assert printer.bed_size_x_mm == 180
        assert printer.bed_size_y_mm == 180
        assert printer.bed_size_z_mm == 180
        assert printer.nozzle_diameter_mm == Decimal("0.4")
        assert printer.default_bed_temp == 60
        assert printer.default_nozzle_temp == 220
        assert printer.capabilities == {"ams": True, "multi_color": True}
        assert printer.is_active is True
        assert printer.notes == "Primary printer"

    def test_printer_base_empty_name_fails(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterBase(name="")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_printer_base_name_too_long_fails(self):
        """Test that name over 100 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterBase(name="A" * 101)
        assert "String should have at most 100 characters" in str(exc_info.value)

    def test_printer_base_invalid_bed_temp_fails(self):
        """Test that bed temperature > 200 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterBase(name="Test", default_bed_temp=250)
        assert "less than or equal to 200" in str(exc_info.value)

    def test_printer_base_invalid_nozzle_temp_fails(self):
        """Test that nozzle temperature > 500 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterBase(name="Test", default_nozzle_temp=600)
        assert "less than or equal to 500" in str(exc_info.value)

    def test_printer_base_invalid_nozzle_diameter_fails(self):
        """Test that nozzle diameter outside 0.1-2.0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterBase(name="Test", nozzle_diameter_mm=Decimal("0.05"))
        assert "greater than or equal to" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            PrinterBase(name="Test", nozzle_diameter_mm=Decimal("2.5"))
        assert "less than or equal to" in str(exc_info.value)

    def test_printer_base_invalid_bed_size_fails(self):
        """Test that bed size < 1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterBase(name="Test", bed_size_x_mm=0)
        assert "greater than or equal to 1" in str(exc_info.value)


class TestPrinterCreate:
    """Tests for PrinterCreate schema."""

    def test_printer_create_valid(self):
        """Test creating a valid printer."""
        data = {
            "name": "Bambu A1",
            "manufacturer": "Bambu Lab",
            "bed_size_x_mm": 256,
            "bed_size_y_mm": 256,
            "bed_size_z_mm": 256,
        }
        printer = PrinterCreate(**data)
        assert printer.name == "Bambu A1"
        assert printer.manufacturer == "Bambu Lab"

    def test_printer_create_inherits_base(self):
        """Test that PrinterCreate inherits from PrinterBase."""
        assert issubclass(PrinterCreate, PrinterBase)


class TestPrinterUpdate:
    """Tests for PrinterUpdate schema."""

    def test_printer_update_all_optional(self):
        """Test that all fields are optional for update."""
        update = PrinterUpdate()
        assert update.name is None
        assert update.manufacturer is None
        assert update.is_active is None

    def test_printer_update_partial(self):
        """Test partial update with only some fields."""
        data = {
            "name": "Updated Name",
            "is_active": False,
        }
        update = PrinterUpdate(**data)
        assert update.name == "Updated Name"
        assert update.is_active is False
        assert update.manufacturer is None
        assert update.bed_size_x_mm is None

    def test_printer_update_validation_still_applies(self):
        """Test that validation still applies even for optional fields."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterUpdate(name="")  # Empty name should fail
        assert "String should have at least 1 character" in str(exc_info.value)


class TestPrinterResponse:
    """Tests for PrinterResponse schema."""

    def test_printer_response_valid(self):
        """Test creating a valid PrinterResponse."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "name": "Bambu A1 Mini",
            "manufacturer": "Bambu Lab",
            "model": "A1 Mini",
            "bed_size_x_mm": 180,
            "bed_size_y_mm": 180,
            "bed_size_z_mm": 180,
            "nozzle_diameter_mm": Decimal("0.4"),
            "default_bed_temp": 60,
            "default_nozzle_temp": 220,
            "capabilities": {"ams": True},
            "is_active": True,
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }
        response = PrinterResponse(**data)
        assert response.name == "Bambu A1 Mini"
        assert response.manufacturer == "Bambu Lab"

    def test_printer_response_bed_size_str_computed(self):
        """Test bed_size_str computed field."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "name": "Test Printer",
            "bed_size_x_mm": 180,
            "bed_size_y_mm": 180,
            "bed_size_z_mm": 180,
            "nozzle_diameter_mm": Decimal("0.4"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = PrinterResponse(**data)
        assert response.bed_size_str == "180x180x180"

    def test_printer_response_bed_size_str_none_when_incomplete(self):
        """Test bed_size_str is None when bed dimensions are incomplete."""
        now = datetime.now()
        data = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "name": "Test Printer",
            "bed_size_x_mm": 180,
            "bed_size_y_mm": None,  # Missing Y
            "bed_size_z_mm": 180,
            "nozzle_diameter_mm": Decimal("0.4"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        response = PrinterResponse(**data)
        assert response.bed_size_str is None

    def test_printer_response_from_attributes(self):
        """Test that from_attributes is enabled for ORM conversion."""
        assert PrinterResponse.model_config.get("from_attributes") is True


class TestPrinterSummary:
    """Tests for PrinterSummary schema."""

    def test_printer_summary_valid(self):
        """Test creating a valid PrinterSummary."""
        data = {
            "id": uuid4(),
            "name": "Bambu A1 Mini",
            "manufacturer": "Bambu Lab",
            "model": "A1 Mini",
            "is_active": True,
        }
        summary = PrinterSummary(**data)
        assert summary.name == "Bambu A1 Mini"
        assert summary.manufacturer == "Bambu Lab"
        assert summary.is_active is True

    def test_printer_summary_minimal(self):
        """Test PrinterSummary with minimal fields."""
        data = {
            "id": uuid4(),
            "name": "Test Printer",
        }
        summary = PrinterSummary(**data)
        assert summary.name == "Test Printer"
        assert summary.manufacturer is None
        assert summary.model is None
        assert summary.is_active is True  # Default

    def test_printer_summary_from_attributes(self):
        """Test that from_attributes is enabled for ORM conversion."""
        assert PrinterSummary.model_config.get("from_attributes") is True


class TestPrinterListResponse:
    """Tests for PrinterListResponse schema."""

    def test_printer_list_response_valid(self):
        """Test creating a valid PrinterListResponse."""
        now = datetime.now()
        printer_data = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "name": "Test Printer",
            "nozzle_diameter_mm": Decimal("0.4"),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        data = {
            "printers": [PrinterResponse(**printer_data)],
            "total": 1,
            "skip": 0,
            "limit": 10,
        }
        response = PrinterListResponse(**data)
        assert len(response.printers) == 1
        assert response.total == 1
        assert response.skip == 0
        assert response.limit == 10

    def test_printer_list_response_empty(self):
        """Test PrinterListResponse with empty list."""
        data = {
            "printers": [],
            "total": 0,
            "skip": 0,
            "limit": 10,
        }
        response = PrinterListResponse(**data)
        assert len(response.printers) == 0
        assert response.total == 0


class TestPrinterSchemaEdgeCases:
    """Edge case tests for Printer schemas."""

    def test_capabilities_as_empty_dict(self):
        """Test that empty capabilities dict is valid."""
        printer = PrinterCreate(name="Test", capabilities={})
        assert printer.capabilities == {}

    def test_capabilities_with_nested_data(self):
        """Test capabilities with nested data structures."""
        caps = {
            "ams": True,
            "materials": ["PLA", "PETG", "ABS"],
            "features": {
                "auto_leveling": True,
                "enclosure": False,
            },
        }
        printer = PrinterCreate(name="Test", capabilities=caps)
        assert printer.capabilities == caps
        assert printer.capabilities["materials"] == ["PLA", "PETG", "ABS"]

    def test_decimal_nozzle_diameter_precision(self):
        """Test that nozzle diameter handles various decimal inputs."""
        printer1 = PrinterCreate(name="Test", nozzle_diameter_mm=0.6)
        assert printer1.nozzle_diameter_mm == Decimal("0.6")

        printer2 = PrinterCreate(name="Test", nozzle_diameter_mm="0.25")
        assert printer2.nozzle_diameter_mm == Decimal("0.25")

    def test_temperature_edge_values(self):
        """Test temperature at edge values."""
        # Min values (0)
        printer = PrinterCreate(name="Test", default_bed_temp=0, default_nozzle_temp=0)
        assert printer.default_bed_temp == 0
        assert printer.default_nozzle_temp == 0

        # Max values
        printer = PrinterCreate(name="Test", default_bed_temp=200, default_nozzle_temp=500)
        assert printer.default_bed_temp == 200
        assert printer.default_nozzle_temp == 500
