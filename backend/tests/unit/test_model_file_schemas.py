"""
Tests for ModelFile Pydantic schemas (3D model files).
"""

import pytest
from pydantic import ValidationError

from app.schemas.model_file import (
    FileLocation,
    LocalPathValidationRequest,
    LocalPathValidationResponse,
    ModelFileBase,
    ModelFileCreate,
    ModelFileListResponse,
    ModelFileLocalCreate,
    ModelFileType,
    ModelFileUpdate,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestModelFileType:
    def test_all_values(self):
        assert ModelFileType.SOURCE_STL == "source_stl"
        assert ModelFileType.SOURCE_3MF == "source_3mf"
        assert ModelFileType.SLICER_PROJECT == "slicer_project"
        assert ModelFileType.GCODE == "gcode"
        assert ModelFileType.PLATE_LAYOUT == "plate_layout"


class TestFileLocation:
    def test_all_values(self):
        assert FileLocation.UPLOADED == "uploaded"
        assert FileLocation.LOCAL_REFERENCE == "local_reference"


class TestModelFileBase:
    def test_defaults(self):
        f = ModelFileBase(file_type=ModelFileType.SOURCE_STL)
        assert f.is_primary is False
        assert f.part_name is None
        assert f.version is None
        assert f.notes is None

    def test_gcode_type(self):
        f = ModelFileBase(file_type=ModelFileType.GCODE, is_primary=True)
        assert f.file_type == ModelFileType.GCODE
        assert f.is_primary is True

    def test_part_name_max_100(self):
        f = ModelFileBase(file_type=ModelFileType.SOURCE_STL, part_name="P" * 100)
        assert len(f.part_name) == 100

    def test_part_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelFileBase(file_type=ModelFileType.SOURCE_STL, part_name="P" * 101)

    def test_version_max_50(self):
        f = ModelFileBase(file_type=ModelFileType.SOURCE_3MF, version="V" * 50)
        assert len(f.version) == 50

    def test_version_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelFileBase(file_type=ModelFileType.SOURCE_3MF, version="V" * 51)

    def test_file_type_required(self):
        with pytest.raises(ValidationError):
            ModelFileBase()


class TestModelFileCreate:
    def test_valid(self):
        f = ModelFileCreate(file_type=ModelFileType.GCODE)
        assert f.file_type == ModelFileType.GCODE
        assert f.is_primary is False


class TestModelFileLocalCreate:
    def test_valid(self):
        f = ModelFileLocalCreate(
            file_type=ModelFileType.SOURCE_STL,
            local_path="/home/jonathan/models/dragon.stl",
        )
        assert f.local_path == "/home/jonathan/models/dragon.stl"

    def test_local_path_required(self):
        with pytest.raises(ValidationError):
            ModelFileLocalCreate(file_type=ModelFileType.SOURCE_STL)

    def test_local_path_max_1000(self):
        f = ModelFileLocalCreate(
            file_type=ModelFileType.GCODE,
            local_path="/" + "a" * 998,
        )
        assert len(f.local_path) == 999

    def test_local_path_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelFileLocalCreate(
                file_type=ModelFileType.GCODE,
                local_path="/" + "a" * 1000,
            )

    def test_with_all_fields(self):
        f = ModelFileLocalCreate(
            file_type=ModelFileType.SLICER_PROJECT,
            local_path="/models/dragon_v2.3mf",
            part_name="Body",
            version="v2.1",
            is_primary=True,
            notes="Optimized for Bambu X1C",
        )
        assert f.is_primary is True
        assert f.notes == "Optimized for Bambu X1C"


class TestModelFileUpdate:
    def test_all_optional(self):
        u = ModelFileUpdate()
        assert u.part_name is None
        assert u.version is None
        assert u.is_primary is None
        assert u.notes is None

    def test_partial_update(self):
        u = ModelFileUpdate(is_primary=True, notes="Updated notes")
        assert u.is_primary is True

    def test_part_name_max_100(self):
        u = ModelFileUpdate(part_name="P" * 100)
        assert len(u.part_name) == 100

    def test_part_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ModelFileUpdate(part_name="P" * 101)


class TestModelFileListResponse:
    def test_empty(self):
        r = ModelFileListResponse(files=[], total=0)
        assert r.total == 0
        assert r.files == []

    def test_with_total(self):
        r = ModelFileListResponse(files=[], total=5)
        assert r.total == 5


class TestLocalPathValidationRequest:
    def test_valid(self):
        r = LocalPathValidationRequest(path="/home/jonathan/models/dragon.stl")
        assert r.path == "/home/jonathan/models/dragon.stl"

    def test_required(self):
        with pytest.raises(ValidationError):
            LocalPathValidationRequest()


class TestLocalPathValidationResponse:
    def test_file_exists(self):
        r = LocalPathValidationResponse(
            path="/models/dragon.stl",
            exists=True,
            is_file=True,
            file_size=204800,
            filename="dragon.stl",
        )
        assert r.exists is True
        assert r.filename == "dragon.stl"

    def test_does_not_exist(self):
        r = LocalPathValidationResponse(path="/missing/file.stl", exists=False)
        assert r.exists is False
        assert r.is_file is False
        assert r.file_size is None
        assert r.filename is None
