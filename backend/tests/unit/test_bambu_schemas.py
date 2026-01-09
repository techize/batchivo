"""
Unit tests for Bambu Lab integration Pydantic schemas.

Tests validation rules and computed properties for:
- PrinterConnectionCreate/Update/Response schemas
- AMSSlotMappingCreate/Response schemas
- BambuPrinterStatus schema
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.printer_connection import (
    ConnectionType,
    PrinterConnectionCreate,
    PrinterConnectionResponse,
    PrinterConnectionUpdate,
)
from app.schemas.ams_slot_mapping import (
    AMSSlotMappingCreate,
    AMSSlotMappingResponse,
    AMSTrayStatus,
    SpoolSummaryForAMS,
)


class TestPrinterConnectionSchemas:
    """Tests for printer connection schemas."""

    def test_create_with_defaults(self):
        """Test creating connection config with minimal data."""
        config = PrinterConnectionCreate()

        assert config.connection_type == ConnectionType.MANUAL
        assert config.port == 8883
        assert config.ams_count == 0
        assert config.is_enabled is True

    def test_create_bambu_lan(self):
        """Test creating Bambu LAN connection config."""
        config = PrinterConnectionCreate(
            connection_type=ConnectionType.BAMBU_LAN,
            serial_number="01P00A123456789",
            ip_address="192.168.1.100",
            port=8883,
            access_code="12345678",
            ams_count=1,
        )

        assert config.connection_type == ConnectionType.BAMBU_LAN
        assert config.serial_number == "01P00A123456789"
        assert config.ip_address == "192.168.1.100"
        assert config.access_code == "12345678"
        assert config.ams_count == 1

    def test_create_with_invalid_port(self):
        """Test that invalid port raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterConnectionCreate(port=70000)

        assert "port" in str(exc_info.value)

    def test_create_with_invalid_ams_count(self):
        """Test that invalid AMS count raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            PrinterConnectionCreate(ams_count=5)

        assert "ams_count" in str(exc_info.value)

    def test_ip_address_validation_ipv4(self):
        """Test that valid IPv4 addresses are accepted."""
        config = PrinterConnectionCreate(ip_address="192.168.1.100")
        assert config.ip_address == "192.168.1.100"

    def test_ip_address_validation_hostname(self):
        """Test that hostnames are accepted."""
        config = PrinterConnectionCreate(ip_address="printer.local")
        assert config.ip_address == "printer.local"

    def test_update_partial(self):
        """Test partial update schema."""
        update = PrinterConnectionUpdate(access_code="newcode123")

        assert update.access_code == "newcode123"
        assert update.ip_address is None
        assert update.port is None

    def test_response_masks_access_code(self):
        """Test that response schema masks sensitive data."""
        from datetime import datetime, timezone

        response = PrinterConnectionResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            printer_id=uuid4(),
            connection_type=ConnectionType.BAMBU_LAN,
            access_code="12345678",
            cloud_token="very-secret-token-here",
            port=8883,
            ams_count=1,
            is_enabled=True,
            is_connected=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Access code should be masked
        assert response.access_code == "****5678"
        # Cloud token should be fully masked
        assert response.cloud_token == "****"


class TestAMSSlotMappingSchemas:
    """Tests for AMS slot mapping schemas."""

    def test_create_mapping(self):
        """Test creating AMS slot mapping."""
        mapping = AMSSlotMappingCreate(
            ams_id=0,
            tray_id=2,
            spool_id=uuid4(),
        )

        assert mapping.ams_id == 0
        assert mapping.tray_id == 2
        assert mapping.spool_id is not None

    def test_create_mapping_without_spool(self):
        """Test creating AMS slot mapping without spool (unmapped)."""
        mapping = AMSSlotMappingCreate(
            ams_id=1,
            tray_id=0,
        )

        assert mapping.ams_id == 1
        assert mapping.tray_id == 0
        assert mapping.spool_id is None

    def test_invalid_ams_id(self):
        """Test that invalid AMS ID raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AMSSlotMappingCreate(ams_id=4, tray_id=0)  # Max is 3

        assert "ams_id" in str(exc_info.value)

    def test_invalid_tray_id(self):
        """Test that invalid tray ID raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            AMSSlotMappingCreate(ams_id=0, tray_id=5)  # Max is 3

        assert "tray_id" in str(exc_info.value)

    def test_response_computed_fields(self):
        """Test computed fields in response schema."""
        from datetime import datetime, timezone

        response = AMSSlotMappingResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            printer_id=uuid4(),
            ams_id=2,
            tray_id=1,
            last_reported_color="FF5733AA",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Test computed properties
        assert response.absolute_slot_id == 9  # (2 * 4) + 1 = 9
        assert response.slot_display_name == "AMS 3 Slot 2"  # 1-indexed for display
        assert response.color_hex_normalized == "FF5733"  # RGB without alpha


class TestAMSTrayStatusSchema:
    """Tests for AMS tray status schema (from MQTT)."""

    def test_parse_bambu_filament(self):
        """Test parsing status for Bambu Lab filament with RFID."""
        status = AMSTrayStatus(
            tray_id=0,
            tag_uid="ABC123DEF456",
            tray_type="PLA",
            tray_color="DFE2E3FF",
            tray_weight=1000,
            tray_diameter=1.75,
            nozzle_temp_min=190,
            nozzle_temp_max=240,
            bed_temp=60,
            remain=85,
            tray_info_idx="GFA00",
            tray_sub_brands="Bambu Lab",
        )

        assert status.tray_type == "PLA"
        assert status.remain == 85
        assert status.tag_uid == "ABC123DEF456"
        assert status.tray_sub_brands == "Bambu Lab"

    def test_parse_third_party_filament(self):
        """Test parsing status for third-party filament (no RFID)."""
        status = AMSTrayStatus(
            tray_id=1,
            tray_type="PLA",
            tray_color="FF0000FF",
            remain=50,
        )

        assert status.tag_uid is None
        assert status.tray_info_idx is None
        assert status.remain == 50

    def test_parse_empty_tray(self):
        """Test parsing status for empty tray."""
        status = AMSTrayStatus(
            tray_id=2,
        )

        assert status.tray_type is None
        assert status.remain is None
        assert status.tag_uid is None


class TestSpoolSummaryForAMSSchema:
    """Tests for spool summary schema used in AMS display."""

    def test_remaining_percentage(self):
        """Test remaining percentage calculation."""
        summary = SpoolSummaryForAMS(
            id=uuid4(),
            spool_id="PLA-RED-001",
            brand="Bambu",
            color="Red",
            current_weight=750.0,
            initial_weight=1000.0,
        )

        assert summary.remaining_percentage == 75.0

    def test_remaining_percentage_empty(self):
        """Test remaining percentage when spool is empty."""
        summary = SpoolSummaryForAMS(
            id=uuid4(),
            spool_id="PLA-RED-001",
            brand="Bambu",
            color="Red",
            current_weight=0.0,
            initial_weight=1000.0,
        )

        assert summary.remaining_percentage == 0.0

    def test_remaining_percentage_zero_initial(self):
        """Test remaining percentage when initial weight is zero (edge case)."""
        summary = SpoolSummaryForAMS(
            id=uuid4(),
            spool_id="PLA-RED-001",
            brand="Bambu",
            color="Red",
            current_weight=100.0,
            initial_weight=0.0,
        )

        assert summary.remaining_percentage == 0.0
