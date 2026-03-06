"""Unit tests for MoonrakerAdapter (BATCHIVO-002)."""

import pytest
import httpx
import respx

from app.services.moonraker_adapter import MoonrakerAdapter, MoonrakerConnectionConfig
from app.services.printer_adapter import PrinterAdapterState


BASE_URL = "http://192.168.1.100:7125"


def _config(**kwargs) -> MoonrakerConnectionConfig:
    return MoonrakerConnectionConfig(host="192.168.1.100", port=7125, **kwargs)


def _moonraker_response(
    state: str = "printing",
    progress: float = 0.5,
    filename: str = "test.gcode",
    extruder_temp: float = 210.0,
    bed_temp: float = 60.0,
    print_duration: float = 600.0,
) -> dict:
    """Build a minimal Moonraker printer objects query response."""
    return {
        "result": {
            "status": {
                "print_stats": {
                    "state": state,
                    "filename": filename,
                    "print_duration": print_duration,
                    "total_duration": print_duration,
                },
                "virtual_sdcard": {"progress": progress},
                "extruder": {"temperature": extruder_temp},
                "heater_bed": {"temperature": bed_temp},
            }
        }
    }


class TestMoonrakerConnectionConfig:
    def test_defaults(self):
        cfg = MoonrakerConnectionConfig(host="10.0.0.1")
        assert cfg.port == 7125
        assert cfg.api_key is None

    def test_custom_values(self):
        cfg = MoonrakerConnectionConfig(host="10.0.0.2", port=7777, api_key="secret")
        assert cfg.port == 7777
        assert cfg.api_key == "secret"


class TestMoonrakerAdapterOffline:
    """Adapter must return offline state gracefully when printer is unreachable."""

    @pytest.mark.asyncio
    async def test_connection_refused_returns_offline(self):
        adapter = MoonrakerAdapter(_config())
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                side_effect=httpx.ConnectError("refused")
            )
            state = await adapter.get_status()
        assert state.status == "offline"
        assert state.progress_percent is None
        assert state.job_name is None

    @pytest.mark.asyncio
    async def test_timeout_returns_offline(self):
        adapter = MoonrakerAdapter(_config())
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                side_effect=httpx.ReadTimeout("timeout")
            )
            state = await adapter.get_status()
        assert state.status == "offline"

    @pytest.mark.asyncio
    async def test_server_error_returns_offline(self):
        adapter = MoonrakerAdapter(_config())
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(500)
            )
            state = await adapter.get_status()
        assert state.status == "offline"


class TestMoonrakerAdapterStatusMapping:
    """Moonraker states must map correctly to our normalised status."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "moonraker_state,expected_status",
        [
            ("printing", "printing"),
            ("paused", "paused"),
            ("error", "error"),
            ("standby", "idle"),
            ("complete", "idle"),
            ("cancelled", "idle"),
            ("unknown_state", "idle"),  # Unknown → idle (safe default)
        ],
    )
    async def test_state_mapping(self, moonraker_state: str, expected_status: str):
        adapter = MoonrakerAdapter(_config())
        payload = _moonraker_response(state=moonraker_state)
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(200, json=payload)
            )
            state = await adapter.get_status()
        assert state.status == expected_status


class TestMoonrakerAdapterParsing:
    """Adapter must correctly parse progress, job name, and temperatures."""

    @pytest.mark.asyncio
    async def test_progress_calculated(self):
        adapter = MoonrakerAdapter(_config())
        payload = _moonraker_response(progress=0.75)
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(200, json=payload)
            )
            state = await adapter.get_status()
        assert state.progress_percent == 75.0

    @pytest.mark.asyncio
    async def test_job_name_extracted(self):
        adapter = MoonrakerAdapter(_config())
        payload = _moonraker_response(filename="my_print.gcode")
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(200, json=payload)
            )
            state = await adapter.get_status()
        assert state.job_name == "my_print.gcode"

    @pytest.mark.asyncio
    async def test_temperatures_extracted(self):
        adapter = MoonrakerAdapter(_config())
        payload = _moonraker_response(extruder_temp=215.5, bed_temp=65.0)
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(200, json=payload)
            )
            state = await adapter.get_status()
        assert state.temps["extruder"] == 215.5
        assert state.temps["bed"] == 65.0

    @pytest.mark.asyncio
    async def test_zero_progress_no_eta(self):
        adapter = MoonrakerAdapter(_config())
        payload = _moonraker_response(progress=0.0, print_duration=0.0)
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(200, json=payload)
            )
            state = await adapter.get_status()
        assert state.eta_seconds is None

    @pytest.mark.asyncio
    async def test_eta_calculated_for_active_print(self):
        """ETA must be a positive integer when print is in progress."""
        adapter = MoonrakerAdapter(_config())
        # 50% done in 600s → ~600s remaining
        payload = _moonraker_response(progress=0.5, print_duration=600.0)
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(200, json=payload)
            )
            state = await adapter.get_status()
        assert state.eta_seconds is not None
        assert state.eta_seconds > 0

    @pytest.mark.asyncio
    async def test_empty_filename_returns_none_job_name(self):
        adapter = MoonrakerAdapter(_config())
        payload = _moonraker_response(filename="")
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(200, json=payload)
            )
            state = await adapter.get_status()
        assert state.job_name is None

    @pytest.mark.asyncio
    async def test_missing_temps_returns_empty_dict(self):
        """If extruder / heater_bed keys are absent, temps dict must be empty."""
        adapter = MoonrakerAdapter(_config())
        payload = {
            "result": {
                "status": {
                    "print_stats": {"state": "standby"},
                    "virtual_sdcard": {"progress": 0.0},
                }
            }
        }
        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(
                return_value=httpx.Response(200, json=payload)
            )
            state = await adapter.get_status()
        assert state.temps == {}


class TestMoonrakerAdapterApiKey:
    """API key must be included in request headers when configured."""

    @pytest.mark.asyncio
    async def test_api_key_sent_in_header(self):
        adapter = MoonrakerAdapter(_config(api_key="mykey"))
        payload = _moonraker_response()
        captured: list[httpx.Request] = []

        def capture(request: httpx.Request, *_):
            captured.append(request)
            return httpx.Response(200, json=payload)

        with respx.mock:
            respx.get(f"{BASE_URL}/printer/objects/query").mock(side_effect=capture)
            await adapter.get_status()

        assert len(captured) == 1
        assert captured[0].headers.get("x-api-key") == "mykey"


class TestMoonrakerAdapterProtocol:
    """MoonrakerAdapter must satisfy the PrinterAdapter protocol."""

    def test_implements_printer_adapter_protocol(self):
        from app.services.printer_adapter import PrinterAdapter

        adapter = MoonrakerAdapter(_config())
        assert isinstance(adapter, PrinterAdapter)
