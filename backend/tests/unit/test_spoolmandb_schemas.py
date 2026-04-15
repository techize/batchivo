"""
Tests for SpoolmanDB Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.spoolmandb import (
    SpoolmanDBFilamentBase,
    SpoolmanDBFilamentListResponse,
    SpoolmanDBFilamentWithManufacturer,
    SpoolmanDBManufacturerBase,
    SpoolmanDBManufacturerListResponse,
    SpoolmanDBManufacturerWithCount,
    SpoolmanDBStatsResponse,
    SpoolmanDBSyncResponse,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestSpoolmanDBManufacturerBase:
    def test_valid(self):
        m = SpoolmanDBManufacturerBase(name="Bambu Lab")
        assert m.name == "Bambu Lab"

    def test_name_required(self):
        with pytest.raises(ValidationError):
            SpoolmanDBManufacturerBase()


class TestSpoolmanDBManufacturerWithCount:
    def test_default_count(self):
        m = SpoolmanDBManufacturerWithCount(
            id=uuid4(),
            name="Polymaker",
            is_active=True,
            created_at=_now(),
            updated_at=_now(),
        )
        assert m.filament_count == 0

    def test_nonzero_count(self):
        m = SpoolmanDBManufacturerWithCount(
            id=uuid4(),
            name="Bambu Lab",
            is_active=True,
            filament_count=42,
            created_at=_now(),
            updated_at=_now(),
        )
        assert m.filament_count == 42


class TestSpoolmanDBFilamentBase:
    def _valid(self, **kwargs) -> dict:
        defaults = {
            "external_id": "bambu-pla-basic-white",
            "name": "PLA Basic White",
            "material": "PLA",
            "diameter": 1.75,
            "weight": 1000,
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        f = SpoolmanDBFilamentBase(**self._valid())
        assert f.external_id == "bambu-pla-basic-white"
        assert f.density is None
        assert f.translucent is False
        assert f.glow is False

    def test_with_all_fields(self):
        f = SpoolmanDBFilamentBase(
            **self._valid(
                density=1.24,
                spool_weight=250,
                spool_type="cardboard",
                color_name="White",
                color_hex="FFFFFF",
                extruder_temp=220,
                bed_temp=35,
                finish="matte",
                translucent=True,
                glow=False,
                pattern=None,
                multi_color_direction=None,
                color_hexes=None,
            )
        )
        assert f.density == 1.24
        assert f.color_hex == "FFFFFF"
        assert f.translucent is True

    def test_required_fields_missing_raises(self):
        with pytest.raises(ValidationError):
            SpoolmanDBFilamentBase(external_id="x", name="X", material="PLA")


class TestSpoolmanDBFilamentWithManufacturer:
    def test_valid(self):
        f = SpoolmanDBFilamentWithManufacturer(
            id=uuid4(),
            manufacturer_id=uuid4(),
            external_id="abc",
            name="PETG Black",
            material="PETG",
            diameter=1.75,
            weight=1000,
            is_active=True,
            manufacturer_name="Generic Brand",
            created_at=_now(),
            updated_at=_now(),
        )
        assert f.manufacturer_name == "Generic Brand"


class TestSpoolmanDBFilamentListResponse:
    def test_empty(self):
        r = SpoolmanDBFilamentListResponse(filaments=[], total=0, page=1, page_size=20)
        assert r.total == 0
        assert r.page == 1
        assert r.page_size == 20

    def test_with_pagination(self):
        r = SpoolmanDBFilamentListResponse(filaments=[], total=100, page=3, page_size=20)
        assert r.total == 100
        assert r.page == 3


class TestSpoolmanDBManufacturerListResponse:
    def test_empty(self):
        r = SpoolmanDBManufacturerListResponse(manufacturers=[], total=0)
        assert r.total == 0

    def test_nonzero_total(self):
        r = SpoolmanDBManufacturerListResponse(manufacturers=[], total=10)
        assert r.total == 10


class TestSpoolmanDBSyncResponse:
    def test_valid(self):
        r = SpoolmanDBSyncResponse(
            success=True,
            manufacturers_added=5,
            manufacturers_updated=2,
            filaments_added=100,
            filaments_updated=50,
            message="Sync complete",
        )
        assert r.success is True
        assert r.manufacturers_added == 5
        assert r.filaments_added == 100

    def test_failure(self):
        r = SpoolmanDBSyncResponse(
            success=False,
            manufacturers_added=0,
            manufacturers_updated=0,
            filaments_added=0,
            filaments_updated=0,
            message="Connection timeout",
        )
        assert r.success is False


class TestSpoolmanDBStatsResponse:
    def test_valid_minimal(self):
        r = SpoolmanDBStatsResponse(
            total_manufacturers=10,
            total_filaments=500,
            materials=["PLA", "PETG", "ABS"],
        )
        assert r.total_manufacturers == 10
        assert r.total_filaments == 500
        assert "PLA" in r.materials
        assert r.last_sync is None

    def test_with_last_sync(self):
        ts = _now()
        r = SpoolmanDBStatsResponse(
            total_manufacturers=10,
            total_filaments=500,
            materials=["PLA"],
            last_sync=ts,
        )
        assert r.last_sync == ts

    def test_empty_materials(self):
        r = SpoolmanDBStatsResponse(total_manufacturers=0, total_filaments=0, materials=[])
        assert r.materials == []
