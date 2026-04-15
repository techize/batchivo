"""
Tests for PrinterConnection Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.printer_connection import (
    BambuPrinterStatus,
    ConnectionType,
    PrinterConnectionBase,
    PrinterConnectionCreate,
    PrinterConnectionResponse,
    PrinterConnectionStatus,
    PrinterConnectionUpdate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestConnectionType:
    def test_all_values(self):
        assert ConnectionType.BAMBU_LAN == "bambu_lan"
        assert ConnectionType.BAMBU_CLOUD == "bambu_cloud"
        assert ConnectionType.OCTOPRINT == "octoprint"
        assert ConnectionType.KLIPPER == "klipper"
        assert ConnectionType.MOONRAKER == "moonraker"
        assert ConnectionType.MANUAL == "manual"


class TestPrinterConnectionBase:
    def test_defaults(self):
        c = PrinterConnectionBase()
        assert c.connection_type == ConnectionType.MANUAL
        assert c.serial_number is None
        assert c.ip_address is None
        assert c.port == 8883
        assert c.access_code is None
        assert c.cloud_username is None
        assert c.cloud_token is None
        assert c.ams_count == 0
        assert c.is_enabled is True

    def test_bambu_lan_connection(self):
        c = PrinterConnectionBase(
            connection_type=ConnectionType.BAMBU_LAN,
            serial_number="01S09C450102345",
            ip_address="192.168.1.100",
            port=8883,
            access_code="12345678",
        )
        assert c.connection_type == ConnectionType.BAMBU_LAN
        assert c.serial_number == "01S09C450102345"
        assert c.ip_address == "192.168.1.100"

    def test_serial_number_max_50(self):
        c = PrinterConnectionBase(serial_number="S" * 50)
        assert len(c.serial_number) == 50

    def test_serial_number_too_long_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionBase(serial_number="S" * 51)

    def test_ip_address_max_45(self):
        # IPv6 addresses can be up to 45 chars (including colons)
        c = PrinterConnectionBase(ip_address="192.168.1.1")
        assert c.ip_address == "192.168.1.1"

    def test_ip_address_too_long_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionBase(ip_address="a" * 46)

    def test_port_min_1(self):
        c = PrinterConnectionBase(port=1)
        assert c.port == 1

    def test_port_max_65535(self):
        c = PrinterConnectionBase(port=65535)
        assert c.port == 65535

    def test_port_zero_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionBase(port=0)

    def test_port_above_max_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionBase(port=65536)

    def test_ams_count_zero(self):
        c = PrinterConnectionBase(ams_count=0)
        assert c.ams_count == 0

    def test_ams_count_max_4(self):
        c = PrinterConnectionBase(ams_count=4)
        assert c.ams_count == 4

    def test_ams_count_above_4_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionBase(ams_count=5)

    def test_ams_count_negative_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionBase(ams_count=-1)

    def test_ip_validator_allows_valid_ip(self):
        c = PrinterConnectionBase(ip_address="10.0.0.1")
        assert c.ip_address == "10.0.0.1"

    def test_ip_validator_allows_none(self):
        c = PrinterConnectionBase(ip_address=None)
        assert c.ip_address is None

    def test_access_code_max_100(self):
        c = PrinterConnectionBase(access_code="A" * 100)
        assert len(c.access_code) == 100

    def test_access_code_too_long_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionBase(access_code="A" * 101)

    def test_cloud_username_max_100(self):
        c = PrinterConnectionBase(cloud_username="U" * 100)
        assert len(c.cloud_username) == 100

    def test_cloud_username_too_long_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionBase(cloud_username="U" * 101)


class TestPrinterConnectionCreate:
    def test_inherits_base_defaults(self):
        c = PrinterConnectionCreate()
        assert c.connection_type == ConnectionType.MANUAL
        assert c.port == 8883


class TestPrinterConnectionUpdate:
    def test_all_optional(self):
        u = PrinterConnectionUpdate()
        assert u.connection_type is None
        assert u.serial_number is None
        assert u.ip_address is None
        assert u.port is None
        assert u.access_code is None
        assert u.cloud_username is None
        assert u.cloud_token is None
        assert u.ams_count is None
        assert u.is_enabled is None

    def test_partial_update(self):
        u = PrinterConnectionUpdate(port=8884, is_enabled=False)
        assert u.port == 8884
        assert u.is_enabled is False

    def test_port_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionUpdate(port=0)

    def test_ams_count_above_4_raises(self):
        with pytest.raises(ValidationError):
            PrinterConnectionUpdate(ams_count=5)


class TestPrinterConnectionResponse:
    def _base(self, **kwargs) -> dict:
        now = _now()
        defaults = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "printer_id": uuid4(),
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        r = PrinterConnectionResponse(**self._base())
        assert r.is_connected is False
        assert r.last_connected_at is None
        assert r.connection_error is None

    def test_access_code_masked(self):
        r = PrinterConnectionResponse(**self._base(access_code="12345678"))
        assert r.access_code == "****5678"

    def test_access_code_short_masked(self):
        r = PrinterConnectionResponse(**self._base(access_code="1234"))
        assert r.access_code == "****"

    def test_access_code_none_remains_none(self):
        r = PrinterConnectionResponse(**self._base(access_code=None))
        assert r.access_code is None

    def test_cloud_token_masked(self):
        r = PrinterConnectionResponse(**self._base(cloud_token="secret-token-abc"))
        assert r.cloud_token == "****"

    def test_cloud_token_none_remains_none(self):
        r = PrinterConnectionResponse(**self._base(cloud_token=None))
        assert r.cloud_token is None


class TestPrinterConnectionStatus:
    def test_valid(self):
        s = PrinterConnectionStatus(
            printer_id=uuid4(),
            connection_type=ConnectionType.BAMBU_LAN,
            is_enabled=True,
            is_connected=True,
        )
        assert s.is_connected is True
        assert s.ams_count == 0

    def test_not_connected(self):
        s = PrinterConnectionStatus(
            printer_id=uuid4(),
            connection_type=ConnectionType.MANUAL,
            is_enabled=False,
            is_connected=False,
            connection_error="Connection refused",
        )
        assert s.connection_error == "Connection refused"


class TestBambuPrinterStatus:
    def test_valid_minimal(self):
        s = BambuPrinterStatus(serial_number="01S09C450102345")
        assert s.serial_number == "01S09C450102345"
        assert s.is_online is False
        assert s.print_status is None
        assert s.print_percentage is None

    def test_printing(self):
        s = BambuPrinterStatus(
            serial_number="01S09C450102345",
            is_online=True,
            print_status="RUNNING",
            print_percentage=42,
            current_layer=50,
            total_layers=120,
            remaining_time_minutes=30,
            current_file="model.gcode",
            nozzle_temp=220.5,
            nozzle_target_temp=220.0,
            bed_temp=65.0,
            bed_target_temp=65.0,
            chamber_temp=35.0,
        )
        assert s.is_online is True
        assert s.print_percentage == 42
        assert s.nozzle_temp == 220.5

    def test_with_error(self):
        s = BambuPrinterStatus(
            serial_number="SN123",
            error_code=500,
            error_message="Filament jam",
        )
        assert s.error_code == 500
        assert s.error_message == "Filament jam"
