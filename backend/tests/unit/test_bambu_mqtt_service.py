"""
Unit tests for BambuMQTTService.

Tests MQTT message parsing and state management.
Note: Actual MQTT connections are not tested here (integration tests).
"""

from uuid import uuid4

import pytest

from app.services.bambu_mqtt import (
    BambuConnectionConfig,
    BambuMQTTService,
    BambuPrinterState,
)


class TestBambuPrinterState:
    """Tests for BambuPrinterState dataclass."""

    def test_default_state(self):
        """Test default state values."""
        state = BambuPrinterState(serial_number="01P00A123456789")

        assert state.serial_number == "01P00A123456789"
        assert state.is_online is False
        assert state.print_status is None
        assert state.print_percentage == 0
        assert state.tray_now == 255  # 255 means no tray selected
        assert state.hms_errors == []

    def test_state_with_print_progress(self):
        """Test state with print progress data."""
        state = BambuPrinterState(
            serial_number="01P00A123456789",
            is_online=True,
            print_status="RUNNING",
            print_percentage=45,
            current_layer=150,
            total_layers=300,
            remaining_time_seconds=7200,
            current_file="dragon.3mf",
        )

        assert state.print_status == "RUNNING"
        assert state.print_percentage == 45
        assert state.current_layer == 150
        assert state.remaining_time_seconds == 7200


class TestBambuConnectionConfig:
    """Tests for BambuConnectionConfig dataclass."""

    def test_config_creation(self):
        """Test creating connection config."""
        config = BambuConnectionConfig(
            printer_id=uuid4(),
            serial_number="01P00A123456789",
            ip_address="192.168.1.100",
            port=8883,
            access_code="12345678",
        )

        assert config.serial_number == "01P00A123456789"
        assert config.ip_address == "192.168.1.100"
        assert config.port == 8883
        assert config.use_tls is True  # Default


class TestBambuMQTTService:
    """Tests for BambuMQTTService."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = BambuMQTTService()

        assert service._connections == {}
        assert service._states == {}
        assert service._configs == {}
        assert service._sequence_id == 0

    def test_get_next_sequence_id(self):
        """Test sequence ID increments."""
        service = BambuMQTTService()

        seq1 = service._get_next_sequence_id()
        seq2 = service._get_next_sequence_id()
        seq3 = service._get_next_sequence_id()

        assert seq1 == "1"
        assert seq2 == "2"
        assert seq3 == "3"

    def test_is_connected_not_connected(self):
        """Test is_connected returns False when not connected."""
        service = BambuMQTTService()
        printer_id = uuid4()

        assert service.is_connected(printer_id) is False

    def test_get_connected_printers_empty(self):
        """Test get_connected_printers returns empty list."""
        service = BambuMQTTService()

        assert service.get_connected_printers() == []

    def test_get_printer_state_not_exists(self):
        """Test get_printer_state returns None for unknown printer."""
        service = BambuMQTTService()
        printer_id = uuid4()

        assert service.get_printer_state(printer_id) is None

    def test_get_printer_status_not_exists(self):
        """Test get_printer_status returns None for unknown printer."""
        service = BambuMQTTService()
        printer_id = uuid4()

        assert service.get_printer_status(printer_id) is None

    def test_get_ams_status_not_exists(self):
        """Test get_ams_status returns empty list for unknown printer."""
        service = BambuMQTTService()
        printer_id = uuid4()

        assert service.get_ams_status(printer_id) == []


class TestBambuMQTTServiceCallbacks:
    """Tests for callback registration."""

    def test_register_callback(self):
        """Test registering a callback."""
        service = BambuMQTTService()
        callback_called = []

        def my_callback(*args):
            callback_called.append(args)

        service.register_callback("status_update", my_callback)

        assert my_callback in service._callbacks["status_update"]

    def test_unregister_callback(self):
        """Test unregistering a callback."""
        service = BambuMQTTService()

        def my_callback(*args):
            pass

        service.register_callback("status_update", my_callback)
        service.unregister_callback("status_update", my_callback)

        assert my_callback not in service._callbacks["status_update"]

    def test_unregister_nonexistent_callback(self):
        """Test unregistering a non-existent callback doesn't raise."""
        service = BambuMQTTService()

        def my_callback(*args):
            pass

        # Should not raise
        service.unregister_callback("status_update", my_callback)


class TestBambuMQTTServiceMessageParsing:
    """Tests for MQTT message parsing."""

    @pytest.mark.asyncio
    async def test_update_print_status(self):
        """Test parsing print status from MQTT payload."""
        service = BambuMQTTService()
        state = BambuPrinterState(serial_number="01P00A123456789")

        print_data = {
            "gcode_state": "RUNNING",
            "mc_percent": 45,
            "layer_num": 150,
            "total_layer_num": 300,
            "mc_remaining_time": 7200,
            "gcode_file": "dragon.3mf",
            "subtask_name": "Plate_1",
            "nozzle_temper": 220.5,
            "nozzle_target_temper": 220.0,
            "bed_temper": 60.2,
            "bed_target_temper": 60.0,
            "chamber_temper": 35.0,
        }

        await service._update_print_status(state, print_data)

        assert state.print_status == "RUNNING"
        assert state.print_percentage == 45
        assert state.current_layer == 150
        assert state.total_layers == 300
        assert state.remaining_time_seconds == 7200
        assert state.current_file == "dragon.3mf"
        assert state.subtask_name == "Plate_1"
        assert state.nozzle_temp == 220.5
        assert state.bed_temp == 60.2
        assert state.chamber_temp == 35.0

    @pytest.mark.asyncio
    async def test_update_ams_status(self):
        """Test parsing AMS status from MQTT payload."""
        service = BambuMQTTService()
        printer_id = uuid4()
        state = BambuPrinterState(serial_number="01P00A123456789")
        service._states[printer_id] = state

        print_data = {
            "ams": {
                "tray_now": "5",
                "ams_exist_bits": "1",
                "tray_exist_bits": "f",
                "tray_is_bbl_bits": "e",
                "ams": [
                    {
                        "id": "0",
                        "humidity": "3",
                        "temp": "25.0",
                        "tray": [
                            {
                                "id": "0",
                                "tag_uid": "ABC123",
                                "tray_type": "PLA",
                                "tray_color": "DFE2E3FF",
                                "remain": 85,
                            },
                            {
                                "id": "1",
                                "tray_type": "PETG",
                                "tray_color": "FF0000FF",
                                "remain": 50,
                            },
                        ],
                    }
                ],
            }
        }

        await service._update_ams_status(printer_id, state, print_data)

        assert state.tray_now == 5
        assert state.ams_exist_bits == "1"
        assert state.tray_exist_bits == "f"
        assert state.tray_is_bbl_bits == "e"
        assert len(state.ams_units) == 1
        assert state.ams_units[0]["id"] == "0"

    @pytest.mark.asyncio
    async def test_get_ams_status_parsed(self):
        """Test getting AMS status as Pydantic models."""
        service = BambuMQTTService()
        printer_id = uuid4()
        state = BambuPrinterState(
            serial_number="01P00A123456789",
            ams_units=[
                {
                    "id": "0",
                    "humidity": "3",
                    "temp": "25.0",
                    "tray": [
                        {
                            "id": "0",
                            "tag_uid": "ABC123",
                            "tray_type": "PLA",
                            "tray_color": "DFE2E3FF",
                            "tray_weight": "1000",
                            "tray_diameter": "1.75",
                            "nozzle_temp_min": "190",
                            "nozzle_temp_max": "240",
                            "remain": 85,
                        },
                    ],
                }
            ],
        )
        service._states[printer_id] = state

        ams_status = service.get_ams_status(printer_id)

        assert len(ams_status) == 1
        assert ams_status[0].ams_id == 0
        assert ams_status[0].humidity == 3.0
        assert ams_status[0].temperature == 25.0
        assert len(ams_status[0].trays) == 1

        tray = ams_status[0].trays[0]
        assert tray.tray_id == 0
        assert tray.tray_type == "PLA"
        assert tray.remain == 85
        assert tray.tag_uid == "ABC123"

    @pytest.mark.asyncio
    async def test_get_printer_status_from_state(self):
        """Test converting state to BambuPrinterStatus."""
        service = BambuMQTTService()
        printer_id = uuid4()
        state = BambuPrinterState(
            serial_number="01P00A123456789",
            is_online=True,
            print_status="RUNNING",
            print_percentage=45,
            current_layer=150,
            total_layers=300,
            remaining_time_seconds=3600,  # 60 minutes
            current_file="dragon.3mf",
            nozzle_temp=220.0,
            nozzle_target_temp=220.0,
            bed_temp=60.0,
            bed_target_temp=60.0,
            chamber_temp=35.0,
        )
        service._states[printer_id] = state

        status = service.get_printer_status(printer_id)

        assert status is not None
        assert status.serial_number == "01P00A123456789"
        assert status.is_online is True
        assert status.print_status == "RUNNING"
        assert status.print_percentage == 45
        assert status.current_layer == 150
        assert status.total_layers == 300
        assert status.remaining_time_minutes == 60  # Converted from seconds
        assert status.nozzle_temp == 220.0
        assert status.bed_temp == 60.0


class TestBambuMQTTServiceStateManagement:
    """Tests for printer state management."""

    def test_state_stored_on_connect_init(self):
        """Test that state is initialized when setting up connection."""
        service = BambuMQTTService()
        printer_id = uuid4()

        # Simulate state initialization that happens in connect()
        config = BambuConnectionConfig(
            printer_id=printer_id,
            serial_number="01P00A123456789",
            ip_address="192.168.1.100",
            access_code="12345678",
        )
        service._configs[printer_id] = config
        service._states[printer_id] = BambuPrinterState(serial_number=config.serial_number)

        state = service.get_printer_state(printer_id)
        assert state is not None
        assert state.serial_number == "01P00A123456789"
        assert state.is_online is False

    def test_connected_printers_list(self):
        """Test getting list of connected printers."""
        service = BambuMQTTService()
        printer1_id = uuid4()
        printer2_id = uuid4()
        printer3_id = uuid4()

        # Add states with different online status
        service._states[printer1_id] = BambuPrinterState(serial_number="PRINTER1", is_online=True)
        service._states[printer2_id] = BambuPrinterState(serial_number="PRINTER2", is_online=False)
        service._states[printer3_id] = BambuPrinterState(serial_number="PRINTER3", is_online=True)

        connected = service.get_connected_printers()

        assert len(connected) == 2
        assert printer1_id in connected
        assert printer3_id in connected
        assert printer2_id not in connected
