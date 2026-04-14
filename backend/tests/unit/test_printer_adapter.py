"""
Tests for PrinterAdapterState dataclass and PrinterAdapter protocol.
"""

from app.services.printer_adapter import PrinterAdapter, PrinterAdapterState


class TestPrinterAdapterState:
    def test_default_values(self):
        state = PrinterAdapterState(status="idle")
        assert state.status == "idle"
        assert state.progress_percent is None
        assert state.job_name is None
        assert state.temps == {}
        assert state.eta_seconds is None

    def test_all_fields(self):
        state = PrinterAdapterState(
            status="printing",
            progress_percent=45.5,
            job_name="caelith_body.gcode",
            temps={"extruder": 215.0, "bed": 60.0},
            eta_seconds=1800,
        )
        assert state.status == "printing"
        assert state.progress_percent == 45.5
        assert state.job_name == "caelith_body.gcode"
        assert state.temps == {"extruder": 215.0, "bed": 60.0}
        assert state.eta_seconds == 1800

    def test_status_values(self):
        for status in ("printing", "paused", "error", "idle", "offline"):
            state = PrinterAdapterState(status=status)
            assert state.status == status

    def test_temps_default_is_independent(self):
        """Each instance should get its own empty dict, not a shared reference."""
        a = PrinterAdapterState(status="idle")
        b = PrinterAdapterState(status="idle")
        a.temps["extruder"] = 200.0
        assert b.temps == {}

    def test_partial_temps(self):
        state = PrinterAdapterState(status="printing", temps={"extruder": 215.0})
        assert "extruder" in state.temps
        assert "bed" not in state.temps

    def test_zero_progress(self):
        state = PrinterAdapterState(status="printing", progress_percent=0.0)
        assert state.progress_percent == 0.0

    def test_full_progress(self):
        state = PrinterAdapterState(status="printing", progress_percent=100.0)
        assert state.progress_percent == 100.0

    def test_equality(self):
        a = PrinterAdapterState(status="idle", eta_seconds=None)
        b = PrinterAdapterState(status="idle", eta_seconds=None)
        assert a == b

    def test_inequality_on_status(self):
        a = PrinterAdapterState(status="idle")
        b = PrinterAdapterState(status="printing")
        assert a != b


class TestPrinterAdapterProtocol:
    def test_protocol_is_runtime_checkable(self):
        """PrinterAdapter is decorated with @runtime_checkable."""
        # Objects without the required async methods should not pass
        assert not isinstance(object(), PrinterAdapter)

    def test_conforming_class_passes_isinstance(self):
        """A class with all required methods passes the runtime isinstance check."""

        class ConcreteAdapter:
            async def get_status(self) -> PrinterAdapterState:
                return PrinterAdapterState(status="idle")

            async def pause(self) -> None:
                pass

            async def resume(self) -> None:
                pass

            async def cancel(self) -> None:
                pass

        adapter = ConcreteAdapter()
        assert isinstance(adapter, PrinterAdapter)

    def test_class_missing_method_fails_isinstance(self):
        """A class missing cancel() should not satisfy the Protocol."""

        class IncompleteAdapter:
            async def get_status(self) -> PrinterAdapterState:
                return PrinterAdapterState(status="idle")

            async def pause(self) -> None:
                pass

            async def resume(self) -> None:
                pass

        adapter = IncompleteAdapter()
        assert not isinstance(adapter, PrinterAdapter)
