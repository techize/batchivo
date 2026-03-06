"""Base protocol and dataclasses for printer adapters.

All adapter implementations must conform to the PrinterAdapter protocol.
"""

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class PrinterAdapterState:
    """Normalised state returned by any printer adapter."""

    status: str  # 'printing' | 'paused' | 'error' | 'idle' | 'offline'
    progress_percent: Optional[float] = None
    job_name: Optional[str] = None
    # { 'extruder': float, 'bed': float } — keys may be absent
    temps: dict[str, float] = field(default_factory=dict)
    eta_seconds: Optional[int] = None


@runtime_checkable
class PrinterAdapter(Protocol):
    """Protocol that every printer adapter must satisfy."""

    async def get_status(self) -> PrinterAdapterState:
        """Return the current printer state."""
        ...

    async def pause(self) -> None:
        """Pause the current print."""
        ...

    async def resume(self) -> None:
        """Resume a paused print."""
        ...

    async def cancel(self) -> None:
        """Cancel the current print."""
        ...
