"""
Tests for AMS Slot Mapping Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.ams_slot_mapping import (
    AMSFullStatus,
    AMSSlotBulkMapRequest,
    AMSSlotListResponse,
    AMSSlotMappingBase,
    AMSSlotMappingCreate,
    AMSSlotMappingUpdate,
    AMSStatusFromMQTT,
    AMSTrayStatus,
    SpoolSummaryForAMS,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestAMSSlotMappingBase:
    def test_valid_minimal(self):
        m = AMSSlotMappingBase(ams_id=0, tray_id=0)
        assert m.ams_id == 0
        assert m.tray_id == 0
        assert m.spool_id is None

    def test_max_values(self):
        m = AMSSlotMappingBase(ams_id=3, tray_id=3)
        assert m.ams_id == 3
        assert m.tray_id == 3

    def test_with_spool_id(self):
        sid = uuid4()
        m = AMSSlotMappingBase(ams_id=1, tray_id=2, spool_id=sid)
        assert m.spool_id == sid

    def test_ams_id_negative_raises(self):
        with pytest.raises(ValidationError):
            AMSSlotMappingBase(ams_id=-1, tray_id=0)

    def test_ams_id_above_max_raises(self):
        with pytest.raises(ValidationError):
            AMSSlotMappingBase(ams_id=4, tray_id=0)

    def test_tray_id_negative_raises(self):
        with pytest.raises(ValidationError):
            AMSSlotMappingBase(ams_id=0, tray_id=-1)

    def test_tray_id_above_max_raises(self):
        with pytest.raises(ValidationError):
            AMSSlotMappingBase(ams_id=0, tray_id=4)


class TestAMSSlotMappingCreate:
    def test_inherits_base(self):
        c = AMSSlotMappingCreate(ams_id=0, tray_id=1)
        assert c.ams_id == 0
        assert c.tray_id == 1


class TestAMSSlotMappingUpdate:
    def test_all_optional(self):
        u = AMSSlotMappingUpdate()
        assert u.spool_id is None

    def test_with_spool_id(self):
        sid = uuid4()
        u = AMSSlotMappingUpdate(spool_id=sid)
        assert u.spool_id == sid

    def test_clear_spool_id(self):
        u = AMSSlotMappingUpdate(spool_id=None)
        assert u.spool_id is None


class TestAMSSlotMappingResponse:
    """Tests for AMSSlotMappingResponse via computed_field assertions."""

    def _base_data(self, **kwargs):
        now = _now()
        defaults = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "printer_id": uuid4(),
            "ams_id": 0,
            "tray_id": 0,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(kwargs)
        return defaults

    def _make(self, **kwargs):
        from app.schemas.ams_slot_mapping import AMSSlotMappingResponse

        return AMSSlotMappingResponse(**self._base_data(**kwargs))

    def test_absolute_slot_id_ams0_tray0(self):
        r = self._make(ams_id=0, tray_id=0)
        assert r.absolute_slot_id == 0

    def test_absolute_slot_id_ams0_tray3(self):
        r = self._make(ams_id=0, tray_id=3)
        assert r.absolute_slot_id == 3

    def test_absolute_slot_id_ams1_tray0(self):
        r = self._make(ams_id=1, tray_id=0)
        assert r.absolute_slot_id == 4

    def test_absolute_slot_id_ams3_tray3(self):
        r = self._make(ams_id=3, tray_id=3)
        assert r.absolute_slot_id == 15

    def test_slot_display_name_ams0_tray0(self):
        r = self._make(ams_id=0, tray_id=0)
        assert r.slot_display_name == "AMS 1 Slot 1"

    def test_slot_display_name_ams2_tray1(self):
        r = self._make(ams_id=2, tray_id=1)
        assert r.slot_display_name == "AMS 3 Slot 2"

    def test_color_hex_normalized_8char(self):
        r = self._make(last_reported_color="FF0000FF")
        assert r.color_hex_normalized == "FF0000"

    def test_color_hex_normalized_none(self):
        r = self._make(last_reported_color=None)
        assert r.color_hex_normalized is None

    def test_color_hex_normalized_short(self):
        r = self._make(last_reported_color="FFFF")
        assert r.color_hex_normalized is None

    def test_defaults(self):
        r = self._make()
        assert r.is_auto_mapped is False
        assert r.has_filament is False
        assert r.is_bambu_filament is False
        assert r.spool_id is None


class TestSpoolSummaryForAMS:
    def test_remaining_percentage_normal(self):
        s = SpoolSummaryForAMS(
            id=uuid4(),
            spool_id="SPOOL-001",
            brand="Bambu",
            color="White",
            current_weight=500.0,
            initial_weight=1000.0,
        )
        assert s.remaining_percentage == 50.0

    def test_remaining_percentage_full(self):
        s = SpoolSummaryForAMS(
            id=uuid4(),
            spool_id="SPOOL-002",
            brand="Bambu",
            color="Black",
            current_weight=1000.0,
            initial_weight=1000.0,
        )
        assert s.remaining_percentage == 100.0

    def test_remaining_percentage_zero_initial(self):
        s = SpoolSummaryForAMS(
            id=uuid4(),
            spool_id="SPOOL-003",
            brand="Bambu",
            color="Red",
            current_weight=0.0,
            initial_weight=0.0,
        )
        assert s.remaining_percentage == 0.0

    def test_optional_fields_default_none(self):
        s = SpoolSummaryForAMS(
            id=uuid4(),
            spool_id="SPOOL-004",
            brand="Generic",
            color="Blue",
            current_weight=800.0,
            initial_weight=1000.0,
        )
        assert s.color_hex is None
        assert s.material_type_code is None


class TestAMSTrayStatus:
    def test_valid_minimal(self):
        t = AMSTrayStatus(tray_id=0)
        assert t.tray_id == 0
        assert t.tag_uid is None
        assert t.tray_type is None

    def test_with_all_fields(self):
        t = AMSTrayStatus(
            tray_id=1,
            tag_uid="RFID1234",
            tray_type="PLA",
            tray_color="FF0000FF",
            tray_weight=1000,
            tray_diameter=1.75,
            nozzle_temp_min=190,
            nozzle_temp_max=230,
            bed_temp=35,
            remain=75,
            tray_info_idx="GFL00",
            tray_sub_brands="Bambu PLA Basic",
        )
        assert t.remain == 75
        assert t.tray_color == "FF0000FF"


class TestAMSStatusFromMQTT:
    def test_valid(self):
        s = AMSStatusFromMQTT(ams_id=0, trays=[])
        assert s.ams_id == 0
        assert s.trays == []
        assert s.humidity is None

    def test_with_trays(self):
        trays = [AMSTrayStatus(tray_id=i) for i in range(4)]
        s = AMSStatusFromMQTT(ams_id=1, humidity=45.0, temperature=25.0, trays=trays)
        assert len(s.trays) == 4
        assert s.humidity == 45.0


class TestAMSFullStatus:
    def test_valid_minimal(self):
        s = AMSFullStatus(printer_id=uuid4(), ams_units=[])
        assert s.tray_now is None
        assert s.last_updated_at is None

    def test_with_tray_now(self):
        s = AMSFullStatus(printer_id=uuid4(), ams_units=[], tray_now=2, last_updated_at=_now())
        assert s.tray_now == 2


class TestAMSSlotBulkMapRequest:
    def test_valid_empty(self):
        r = AMSSlotBulkMapRequest(mappings=[])
        assert r.mappings == []

    def test_with_mappings(self):
        r = AMSSlotBulkMapRequest(
            mappings=[
                AMSSlotMappingCreate(ams_id=0, tray_id=0),
                AMSSlotMappingCreate(ams_id=0, tray_id=1, spool_id=uuid4()),
            ]
        )
        assert len(r.mappings) == 2


class TestAMSSlotListResponse:
    def test_valid_empty(self):
        r = AMSSlotListResponse(
            printer_id=uuid4(),
            ams_count=1,
            total_slots=4,
            slots=[],
        )
        assert r.ams_count == 1
        assert r.total_slots == 4
