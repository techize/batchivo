"""Moonraker adapter for Klipper-based printers (including Snapmaker U1).

Moonraker REST API docs: https://moonraker.readthedocs.io/en/latest/web_api/
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from app.services.printer_adapter import PrinterAdapterState

logger = logging.getLogger(__name__)

# Moonraker print_stats.state → our normalised status
_STATE_MAP: dict[str, str] = {
    "printing": "printing",
    "paused": "paused",
    "error": "error",
    "standby": "idle",
    "complete": "idle",
    "cancelled": "idle",
}

_STATUS_OBJECTS = "print_stats&extruder&heater_bed&virtual_sdcard"


@dataclass
class MoonrakerConnectionConfig:
    """Connection configuration for a Moonraker instance."""

    host: str
    port: int = 7125
    api_key: Optional[str] = None


class MoonrakerAdapter:
    """
    Adapter for Klipper/Moonraker printers.

    Communicates with the Moonraker REST API over HTTP.
    Handles offline printers gracefully — always returns a state object,
    never raises exceptions to the caller.
    """

    def __init__(self, config: MoonrakerConnectionConfig) -> None:
        self._config = config
        self._base_url = f"http://{config.host}:{config.port}"
        self._headers: dict[str, str] = {}
        if config.api_key:
            self._headers["X-Api-Key"] = config.api_key

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=5.0,
        )

    @staticmethod
    def _parse_status(data: dict[str, Any]) -> PrinterAdapterState:
        """Parse a Moonraker printer objects query response into PrinterAdapterState."""
        result = data.get("result", {}).get("status", {})

        # -- Status --
        print_stats = result.get("print_stats", {})
        raw_state = print_stats.get("state", "standby").lower()
        status = _STATE_MAP.get(raw_state, "idle")

        # -- Progress --
        vsd = result.get("virtual_sdcard", {})
        raw_progress = vsd.get("progress")
        progress_percent: Optional[float] = (
            round(raw_progress * 100, 1) if raw_progress is not None else None
        )

        # -- Job name --
        job_name: Optional[str] = print_stats.get("filename") or None

        # -- Temperatures --
        temps: dict[str, float] = {}
        extruder = result.get("extruder", {})
        if "temperature" in extruder:
            temps["extruder"] = extruder["temperature"]
        heater_bed = result.get("heater_bed", {})
        if "temperature" in heater_bed:
            temps["bed"] = heater_bed["temperature"]

        # -- ETA --
        # Moonraker doesn't directly expose ETA; derive from print_time remaining
        eta_seconds: Optional[int] = None
        print_duration = print_stats.get("print_duration")
        total_duration = print_stats.get("total_duration")
        if (
            raw_progress is not None
            and raw_progress > 0
            and print_duration is not None
            and print_duration > 0
        ):
            try:
                elapsed = float(print_duration)
                rate = float(raw_progress) / elapsed if elapsed > 0 else 0
                if rate > 0:
                    remaining = (1.0 - float(raw_progress)) / rate
                    eta_seconds = max(0, int(remaining))
            except (ZeroDivisionError, TypeError, ValueError):
                pass
        _ = total_duration  # may be used in the future

        return PrinterAdapterState(
            status=status,
            progress_percent=progress_percent,
            job_name=job_name,
            temps=temps,
            eta_seconds=eta_seconds,
        )

    # ------------------------------------------------------------------
    # Public interface (PrinterAdapter protocol)
    # ------------------------------------------------------------------

    async def get_status(self) -> PrinterAdapterState:
        """
        Fetch current printer state from Moonraker.

        Returns status='offline' if the printer cannot be reached.
        Never raises exceptions.
        """
        try:
            async with self._client() as client:
                resp = await client.get(
                    f"/printer/objects/query?{_STATUS_OBJECTS}"
                )
                resp.raise_for_status()
                return self._parse_status(resp.json())
        except Exception as exc:
            logger.debug("Moonraker unreachable at %s: %s", self._base_url, exc)
            return PrinterAdapterState(status="offline")

    async def pause(self) -> None:
        """Send pause command to Moonraker."""
        async with self._client() as client:
            resp = await client.post("/printer/print/pause")
            resp.raise_for_status()

    async def resume(self) -> None:
        """Send resume command to Moonraker."""
        async with self._client() as client:
            resp = await client.post("/printer/print/resume")
            resp.raise_for_status()

    async def cancel(self) -> None:
        """Send cancel command to Moonraker."""
        async with self._client() as client:
            resp = await client.post("/printer/print/cancel")
            resp.raise_for_status()

    async def get_toolheads(self) -> list[str]:
        """
        Query the toolhead configuration from Moonraker.

        Returns a list of toolhead names (e.g. ['extruder', 'extruder1']).
        Returns empty list if unavailable.
        """
        try:
            async with self._client() as client:
                resp = await client.get("/printer/objects/query?toolhead")
                resp.raise_for_status()
                result = resp.json().get("result", {}).get("status", {})
                toolhead = result.get("toolhead", {})
                extruder = toolhead.get("extruder")
                if extruder:
                    return [extruder]
                return []
        except Exception as exc:
            logger.debug("Could not query toolheads from %s: %s", self._base_url, exc)
            return []
