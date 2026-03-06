"""Known printer model registry.

Provides a catalogue of recognised printer models with their default properties.
Add new models here to make them selectable in the UI and drive adapter logic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PrinterModelInfo:
    """Metadata for a known printer model."""

    model_key: str  # Machine-readable key stored in the DB `model` field
    display_name: str  # Human-readable display name
    manufacturer: str  # Manufacturer name
    connection_type: str  # Default connection type (ConnectionType value)
    has_toolhead_changer: bool  # Supports toolhead / hotend swapping
    has_ams: bool  # Has an automatic material system (multi-filament)


PRINTER_MODELS: dict[str, PrinterModelInfo] = {
    "snapmaker_u1": PrinterModelInfo(
        model_key="snapmaker_u1",
        display_name="Snapmaker U1",
        manufacturer="Snapmaker",
        connection_type="moonraker",
        has_toolhead_changer=True,
        has_ams=False,
    ),
    "bambu_x1c": PrinterModelInfo(
        model_key="bambu_x1c",
        display_name="Bambu X1 Carbon",
        manufacturer="Bambu Lab",
        connection_type="bambu_lan",
        has_toolhead_changer=False,
        has_ams=True,
    ),
    "bambu_p1s": PrinterModelInfo(
        model_key="bambu_p1s",
        display_name="Bambu P1S",
        manufacturer="Bambu Lab",
        connection_type="bambu_lan",
        has_toolhead_changer=False,
        has_ams=True,
    ),
    "bambu_p1p": PrinterModelInfo(
        model_key="bambu_p1p",
        display_name="Bambu P1P",
        manufacturer="Bambu Lab",
        connection_type="bambu_lan",
        has_toolhead_changer=False,
        has_ams=True,
    ),
    "bambu_a1": PrinterModelInfo(
        model_key="bambu_a1",
        display_name="Bambu A1",
        manufacturer="Bambu Lab",
        connection_type="bambu_lan",
        has_toolhead_changer=False,
        has_ams=True,
    ),
    "bambu_a1_mini": PrinterModelInfo(
        model_key="bambu_a1_mini",
        display_name="Bambu A1 Mini",
        manufacturer="Bambu Lab",
        connection_type="bambu_lan",
        has_toolhead_changer=False,
        has_ams=True,
    ),
}


def get_printer_model(model_key: str) -> PrinterModelInfo | None:
    """Return model info for the given key, or None if unknown."""
    return PRINTER_MODELS.get(model_key)


def list_printer_models() -> list[PrinterModelInfo]:
    """Return all known models sorted by manufacturer then display name."""
    return sorted(
        PRINTER_MODELS.values(),
        key=lambda m: (m.manufacturer, m.display_name),
    )
