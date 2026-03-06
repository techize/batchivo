"""Unit tests for printer model registry (BATCHIVO-001)."""

import pytest

from app.services.printer_registry import (
    PRINTER_MODELS,
    PrinterModelInfo,
    get_printer_model,
    list_printer_models,
)


class TestPrinterRegistry:
    """Tests for the printer model registry."""

    def test_snapmaker_u1_exists(self):
        """Snapmaker U1 must be in the registry."""
        assert "snapmaker_u1" in PRINTER_MODELS

    def test_snapmaker_u1_properties(self):
        """Snapmaker U1 has correct properties per BATCHIVO-001."""
        model = PRINTER_MODELS["snapmaker_u1"]
        assert model.display_name == "Snapmaker U1"
        assert model.manufacturer == "Snapmaker"
        assert model.connection_type == "moonraker"
        assert model.has_toolhead_changer is True
        assert model.has_ams is False

    def test_get_printer_model_known_key(self):
        """get_printer_model returns correct model for known key."""
        result = get_printer_model("snapmaker_u1")
        assert result is not None
        assert isinstance(result, PrinterModelInfo)
        assert result.model_key == "snapmaker_u1"

    def test_get_printer_model_unknown_key(self):
        """get_printer_model returns None for unknown key."""
        assert get_printer_model("does_not_exist") is None

    def test_list_printer_models_returns_all(self):
        """list_printer_models returns every registered model."""
        models = list_printer_models()
        assert len(models) == len(PRINTER_MODELS)

    def test_list_printer_models_sorted(self):
        """list_printer_models returns models sorted by manufacturer then name."""
        models = list_printer_models()
        keys = [(m.manufacturer, m.display_name) for m in models]
        assert keys == sorted(keys)

    def test_snapmaker_u1_in_list(self):
        """Snapmaker U1 appears in the full model list."""
        keys = [m.model_key for m in list_printer_models()]
        assert "snapmaker_u1" in keys

    def test_bambu_models_have_ams(self):
        """All Bambu models have AMS support."""
        bambu = [m for m in PRINTER_MODELS.values() if m.manufacturer == "Bambu Lab"]
        assert len(bambu) > 0
        for model in bambu:
            assert model.has_ams is True, f"{model.model_key} should have AMS"

    def test_bambu_models_use_bambu_lan(self):
        """All Bambu models default to bambu_lan connection type."""
        bambu = [m for m in PRINTER_MODELS.values() if m.manufacturer == "Bambu Lab"]
        for model in bambu:
            assert model.connection_type == "bambu_lan", (
                f"{model.model_key} should use bambu_lan"
            )

    def test_all_model_keys_match_dict_keys(self):
        """Each model_key value must equal its dictionary key."""
        for key, model in PRINTER_MODELS.items():
            assert model.model_key == key

    def test_printer_model_info_is_immutable(self):
        """PrinterModelInfo dataclass is frozen (immutable)."""
        model = get_printer_model("snapmaker_u1")
        assert model is not None
        with pytest.raises((AttributeError, TypeError)):
            model.display_name = "Should Fail"  # type: ignore[misc]
