"""
Integration tests for model files API endpoints.

Tests:
- File upload endpoint
- File listing endpoint
- File details endpoint
- File download endpoint
- File update endpoint
- File delete endpoint
- Invalid file type rejection
- Tenant isolation
"""

import io
import zipfile
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.model_file import ModelFileType


# =============================================================================
# Helper Functions
# =============================================================================


def create_minimal_stl() -> bytes:
    """Create minimal valid STL file content (ASCII format)."""
    return b"""solid test
  facet normal 0 0 0
    outer loop
      vertex 0 0 0
      vertex 1 0 0
      vertex 0 1 0
    endloop
  endfacet
endsolid test"""


def create_minimal_3mf() -> bytes:
    """Create minimal valid 3MF file (ZIP with basic structure)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("3D/3dmodel.model", "<model>...</model>")
        zf.writestr("[Content_Types].xml", "<Types>...</Types>")
    return buffer.getvalue()


def create_minimal_gcode() -> bytes:
    """Create minimal valid gcode file content."""
    return b"""; Test gcode
G28 ; Home
G1 X10 Y10 Z0.2 F3000
"""


# =============================================================================
# File Upload Tests
# =============================================================================


class TestModelFilesUpload:
    """Test cases for file upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_stl_file(self, client: AsyncClient, test_model):
        """Test uploading an STL file."""
        stl_content = create_minimal_stl()
        files = {"file": ("test_model.stl", stl_content, "model/stl")}
        data = {"file_type": "source_stl"}

        response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files=files,
            data=data,
        )

        assert response.status_code == 201
        result = response.json()
        assert "file" in result
        assert result["file"]["original_filename"] == "test_model.stl"
        assert result["file"]["file_type"] == "source_stl"
        assert result["file"]["file_size"] == len(stl_content)

    @pytest.mark.asyncio
    async def test_upload_3mf_file(self, client: AsyncClient, test_model):
        """Test uploading a 3MF file."""
        content_3mf = create_minimal_3mf()
        files = {"file": ("test_model.3mf", content_3mf, "model/3mf")}
        data = {"file_type": "source_3mf"}

        response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files=files,
            data=data,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["file"]["original_filename"] == "test_model.3mf"
        assert result["file"]["file_type"] == "source_3mf"

    @pytest.mark.asyncio
    async def test_upload_gcode_file(self, client: AsyncClient, test_model):
        """Test uploading a gcode file."""
        gcode_content = create_minimal_gcode()
        files = {"file": ("test_print.gcode", gcode_content, "text/x-gcode")}
        data = {"file_type": "gcode"}

        response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files=files,
            data=data,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["file"]["original_filename"] == "test_print.gcode"
        assert result["file"]["file_type"] == "gcode"

    @pytest.mark.asyncio
    async def test_upload_with_metadata(self, client: AsyncClient, test_model):
        """Test uploading a file with optional metadata."""
        stl_content = create_minimal_stl()
        files = {"file": ("part_a.stl", stl_content, "model/stl")}
        data = {
            "file_type": "source_stl",
            "part_name": "Base Plate",
            "version": "v1.2",
            "is_primary": "true",
            "notes": "Main structural component",
        }

        response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files=files,
            data=data,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["file"]["part_name"] == "Base Plate"
        assert result["file"]["version"] == "v1.2"
        assert result["file"]["is_primary"] is True
        assert result["file"]["notes"] == "Main structural component"

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client: AsyncClient, test_model):
        """Test that invalid file types are rejected."""
        # Try uploading a Python file
        py_content = b"print('hello world')"
        files = {"file": ("script.py", py_content, "text/x-python")}
        data = {"file_type": "source_stl"}

        response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files=files,
            data=data,
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_to_nonexistent_model(self, client: AsyncClient):
        """Test uploading to a non-existent model returns 400."""
        stl_content = create_minimal_stl()
        files = {"file": ("test.stl", stl_content, "model/stl")}
        data = {"file_type": "source_stl"}
        fake_model_id = uuid4()

        response = await client.post(
            f"/api/v1/models/{fake_model_id}/files",
            files=files,
            data=data,
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()


# =============================================================================
# File Listing Tests
# =============================================================================


class TestModelFilesListing:
    """Test cases for file listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_files_empty(self, client: AsyncClient, test_model):
        """Test listing files when model has no files."""
        response = await client.get(f"/api/v1/models/{test_model.id}/files")

        assert response.status_code == 200
        result = response.json()
        assert result["files"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_files_with_uploads(self, client: AsyncClient, test_model):
        """Test listing files after uploading."""
        # Upload two files
        stl_content = create_minimal_stl()
        gcode_content = create_minimal_gcode()

        await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("model.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl"},
        )
        await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("print.gcode", gcode_content, "text/x-gcode")},
            data={"file_type": "gcode"},
        )

        response = await client.get(f"/api/v1/models/{test_model.id}/files")

        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 2
        assert len(result["files"]) == 2

    @pytest.mark.asyncio
    async def test_list_files_filter_by_type(self, client: AsyncClient, test_model):
        """Test filtering file listing by type."""
        # Upload STL and gcode
        stl_content = create_minimal_stl()
        gcode_content = create_minimal_gcode()

        await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("model.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl"},
        )
        await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("print.gcode", gcode_content, "text/x-gcode")},
            data={"file_type": "gcode"},
        )

        # Filter by source_stl
        response = await client.get(
            f"/api/v1/models/{test_model.id}/files",
            params={"file_type": "source_stl"},
        )

        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 1
        assert result["files"][0]["file_type"] == "source_stl"


# =============================================================================
# File Details Tests
# =============================================================================


class TestModelFileDetails:
    """Test cases for file details endpoint."""

    @pytest.mark.asyncio
    async def test_get_file_details(self, client: AsyncClient, test_model):
        """Test getting file details."""
        # Upload a file first
        stl_content = create_minimal_stl()
        upload_response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("model.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl", "notes": "Test file"},
        )
        file_id = upload_response.json()["file"]["id"]

        # Get details
        response = await client.get(
            f"/api/v1/models/{test_model.id}/files/{file_id}"
        )

        assert response.status_code == 200
        result = response.json()
        assert result["id"] == file_id
        assert result["original_filename"] == "model.stl"
        assert result["notes"] == "Test file"

    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, client: AsyncClient, test_model):
        """Test getting details of non-existent file."""
        fake_file_id = uuid4()

        response = await client.get(
            f"/api/v1/models/{test_model.id}/files/{fake_file_id}"
        )

        assert response.status_code == 404


# =============================================================================
# File Download Tests
# =============================================================================


class TestModelFileDownload:
    """Test cases for file download endpoint."""

    @pytest.mark.asyncio
    async def test_download_file(self, client: AsyncClient, test_model):
        """Test downloading a file."""
        stl_content = create_minimal_stl()
        upload_response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("model.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl"},
        )
        file_id = upload_response.json()["file"]["id"]

        response = await client.get(
            f"/api/v1/models/{test_model.id}/files/{file_id}/download"
        )

        assert response.status_code == 200
        assert response.content == stl_content
        assert "model.stl" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self, client: AsyncClient, test_model):
        """Test downloading non-existent file."""
        fake_file_id = uuid4()

        response = await client.get(
            f"/api/v1/models/{test_model.id}/files/{fake_file_id}/download"
        )

        assert response.status_code == 404


# =============================================================================
# File Update Tests
# =============================================================================


class TestModelFileUpdate:
    """Test cases for file update endpoint."""

    @pytest.mark.asyncio
    async def test_update_file_metadata(self, client: AsyncClient, test_model):
        """Test updating file metadata."""
        # Upload a file
        stl_content = create_minimal_stl()
        upload_response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("model.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl"},
        )
        file_id = upload_response.json()["file"]["id"]

        # Update metadata
        response = await client.patch(
            f"/api/v1/models/{test_model.id}/files/{file_id}",
            json={
                "part_name": "Updated Part",
                "version": "v2.0",
                "notes": "Updated notes",
            },
        )

        assert response.status_code == 200
        result = response.json()
        assert result["part_name"] == "Updated Part"
        assert result["version"] == "v2.0"
        assert result["notes"] == "Updated notes"

    @pytest.mark.asyncio
    async def test_set_file_as_primary(self, client: AsyncClient, test_model):
        """Test setting a file as primary."""
        # Upload two files
        stl_content = create_minimal_stl()

        upload1 = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("model1.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl", "is_primary": "true"},
        )
        file1_id = upload1.json()["file"]["id"]

        upload2 = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("model2.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl"},
        )
        file2_id = upload2.json()["file"]["id"]

        # Set file2 as primary
        response = await client.patch(
            f"/api/v1/models/{test_model.id}/files/{file2_id}",
            json={"is_primary": True},
        )

        assert response.status_code == 200
        assert response.json()["is_primary"] is True

        # Verify file1 is no longer primary
        file1_response = await client.get(
            f"/api/v1/models/{test_model.id}/files/{file1_id}"
        )
        assert file1_response.json()["is_primary"] is False


# =============================================================================
# File Delete Tests
# =============================================================================


class TestModelFileDelete:
    """Test cases for file delete endpoint."""

    @pytest.mark.asyncio
    async def test_delete_file(self, client: AsyncClient, test_model):
        """Test deleting a file."""
        # Upload a file
        stl_content = create_minimal_stl()
        upload_response = await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("model.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl"},
        )
        file_id = upload_response.json()["file"]["id"]

        # Delete it
        response = await client.delete(
            f"/api/v1/models/{test_model.id}/files/{file_id}"
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/models/{test_model.id}/files/{file_id}"
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, client: AsyncClient, test_model):
        """Test deleting non-existent file."""
        fake_file_id = uuid4()

        response = await client.delete(
            f"/api/v1/models/{test_model.id}/files/{fake_file_id}"
        )

        assert response.status_code == 404


# =============================================================================
# Primary File Tests
# =============================================================================


class TestPrimaryFile:
    """Test cases for primary file endpoint."""

    @pytest.mark.asyncio
    async def test_get_primary_file(self, client: AsyncClient, test_model):
        """Test getting the primary file."""
        stl_content = create_minimal_stl()

        # Upload a primary file
        await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("primary.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl", "is_primary": "true"},
        )

        response = await client.get(
            f"/api/v1/models/{test_model.id}/files/primary"
        )

        assert response.status_code == 200
        assert response.json()["original_filename"] == "primary.stl"
        assert response.json()["is_primary"] is True

    @pytest.mark.asyncio
    async def test_get_primary_file_none_exists(self, client: AsyncClient, test_model):
        """Test getting primary file when none exists."""
        response = await client.get(
            f"/api/v1/models/{test_model.id}/files/primary"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_primary_file_filtered_by_type(
        self, client: AsyncClient, test_model
    ):
        """Test getting primary file filtered by type."""
        stl_content = create_minimal_stl()
        gcode_content = create_minimal_gcode()

        # Upload primary STL
        await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("source.stl", stl_content, "model/stl")},
            data={"file_type": "source_stl", "is_primary": "true"},
        )

        # Upload primary gcode
        await client.post(
            f"/api/v1/models/{test_model.id}/files",
            files={"file": ("print.gcode", gcode_content, "text/x-gcode")},
            data={"file_type": "gcode", "is_primary": "true"},
        )

        # Get primary STL
        response = await client.get(
            f"/api/v1/models/{test_model.id}/files/primary",
            params={"file_type": "source_stl"},
        )

        assert response.status_code == 200
        assert response.json()["file_type"] == "source_stl"


# =============================================================================
# Tenant Isolation Tests
# =============================================================================


class TestTenantIsolation:
    """Test cases for tenant isolation in model files API."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_files(
        self, client: AsyncClient, db_session, test_tenant
    ):
        """Test that files from other tenants are not accessible."""
        from app.models.model import Model
        from app.models.model_file import ModelFile
        from decimal import Decimal

        # Create a model for a different tenant
        other_tenant_id = uuid4()
        other_model = Model(
            id=uuid4(),
            tenant_id=other_tenant_id,  # Different tenant!
            sku="OTHER-001",
            name="Other Tenant Model",
            print_time_minutes=30,
            labor_hours=Decimal("0.25"),
            is_active=True,
        )
        db_session.add(other_model)
        await db_session.commit()

        # Create a file for that model
        other_file = ModelFile(
            id=uuid4(),
            tenant_id=other_tenant_id,
            model_id=other_model.id,
            file_type="source_stl",
            file_url="/uploads/models/other/file.stl",
            original_filename="other.stl",
            file_size=100,
            content_type="model/stl",
            is_primary=False,
        )
        db_session.add(other_file)
        await db_session.commit()

        # Try to access the file (should not find it due to tenant isolation)
        response = await client.get(
            f"/api/v1/models/{other_model.id}/files/{other_file.id}"
        )

        # Should get 404 because tenant filter excludes it
        assert response.status_code == 404
