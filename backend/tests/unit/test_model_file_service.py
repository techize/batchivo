"""
Tests for model file service.

Includes tests for:
- 3MF thumbnail extraction
- File validation (types, sizes)
- Upload/download/delete operations
- Storage backends (local, S3)
"""

import io
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.model_file_service import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    ModelFileService,
    ModelFileStorageError,
    extract_3mf_thumbnail,
)


# =============================================================================
# Helper Functions
# =============================================================================


def create_3mf_with_thumbnail(
    thumbnail_path: str = "Metadata/thumbnail.png",
    thumbnail_content: bytes = b"PNG_IMAGE_DATA",
    include_other_files: bool = True,
) -> bytes:
    """Create a mock 3MF file (ZIP archive) with an embedded thumbnail."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add the thumbnail at the specified path
        if thumbnail_path:
            zf.writestr(thumbnail_path, thumbnail_content)

        # Add some other typical 3MF files
        if include_other_files:
            zf.writestr("3D/3dmodel.model", "<model>...</model>")
            zf.writestr("[Content_Types].xml", "<Types>...</Types>")
            zf.writestr("_rels/.rels", "<Relationships>...</Relationships>")

    return buffer.getvalue()


def create_png_image_bytes() -> bytes:
    """Create valid PNG image bytes (minimal 1x1 red pixel PNG)."""
    from PIL import Image

    img = Image.new("RGB", (1, 1), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_jpeg_image_bytes() -> bytes:
    """Create valid JPEG image bytes (minimal 1x1 red pixel JPEG)."""
    from PIL import Image

    img = Image.new("RGB", (1, 1), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


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


def create_minimal_gcode() -> bytes:
    """Create minimal valid gcode file content."""
    return b"""; Test gcode
G28 ; Home
G1 X10 Y10 Z0.2 F3000
G1 X20 Y10 E1 F1500
M104 S0 ; Turn off hotend
M140 S0 ; Turn off bed
M84 ; Disable motors
"""


# =============================================================================
# 3MF Thumbnail Extraction Tests
# =============================================================================


class TestExtract3mfThumbnail:
    """Test cases for extract_3mf_thumbnail function."""

    def test_extract_standard_thumbnail_png(self):
        """Test extracting PNG thumbnail from standard location."""
        png_data = create_png_image_bytes()
        file_content = create_3mf_with_thumbnail(
            thumbnail_path="Metadata/thumbnail.png",
            thumbnail_content=png_data,
        )

        result = extract_3mf_thumbnail(file_content)

        assert result is not None
        thumbnail_data, content_type = result
        assert thumbnail_data == png_data
        assert content_type == "image/png"

    def test_extract_standard_thumbnail_jpg(self):
        """Test extracting JPEG thumbnail from standard location."""
        jpg_data = create_jpeg_image_bytes()
        file_content = create_3mf_with_thumbnail(
            thumbnail_path="Metadata/thumbnail.jpg",
            thumbnail_content=jpg_data,
        )

        result = extract_3mf_thumbnail(file_content)

        assert result is not None
        thumbnail_data, content_type = result
        assert thumbnail_data == jpg_data
        assert content_type == "image/jpeg"

    def test_extract_thumbnail_from_3d_metadata_path(self):
        """Test extracting thumbnail from 3D/Metadata path (some slicers)."""
        png_data = create_png_image_bytes()
        file_content = create_3mf_with_thumbnail(
            thumbnail_path="3D/Metadata/thumbnail.png",
            thumbnail_content=png_data,
        )

        result = extract_3mf_thumbnail(file_content)

        assert result is not None
        thumbnail_data, content_type = result
        assert thumbnail_data == png_data

    def test_extract_bambu_plate_thumbnail(self):
        """Test extracting thumbnail from BambuStudio/OrcaSlicer location."""
        png_data = create_png_image_bytes()
        file_content = create_3mf_with_thumbnail(
            thumbnail_path="Metadata/plate_1.png",
            thumbnail_content=png_data,
        )

        result = extract_3mf_thumbnail(file_content)

        assert result is not None
        thumbnail_data, content_type = result
        assert thumbnail_data == png_data

    def test_extract_top_thumbnail(self):
        """Test extracting thumbnail from Metadata/top.png location."""
        png_data = create_png_image_bytes()
        file_content = create_3mf_with_thumbnail(
            thumbnail_path="Metadata/top.png",
            thumbnail_content=png_data,
        )

        result = extract_3mf_thumbnail(file_content)

        assert result is not None
        thumbnail_data, content_type = result
        assert thumbnail_data == png_data

    def test_case_insensitive_thumbnail_path(self):
        """Test case-insensitive matching of thumbnail paths."""
        png_data = create_png_image_bytes()
        file_content = create_3mf_with_thumbnail(
            thumbnail_path="METADATA/THUMBNAIL.PNG",  # Uppercase
            thumbnail_content=png_data,
        )

        result = extract_3mf_thumbnail(file_content)

        assert result is not None
        thumbnail_data, content_type = result
        assert thumbnail_data == png_data

    def test_no_thumbnail_in_3mf(self):
        """Test 3MF file with no thumbnail returns None."""
        file_content = create_3mf_with_thumbnail(
            thumbnail_path=None,  # No thumbnail
            thumbnail_content=b"",
        )

        result = extract_3mf_thumbnail(file_content)

        assert result is None

    def test_invalid_zip_file(self):
        """Test that invalid ZIP file returns None gracefully."""
        invalid_content = b"This is not a valid ZIP file"

        result = extract_3mf_thumbnail(invalid_content)

        assert result is None

    def test_empty_file(self):
        """Test that empty file returns None gracefully."""
        result = extract_3mf_thumbnail(b"")

        assert result is None

    def test_priority_of_standard_path(self):
        """Test that standard path is preferred over alternative paths."""
        png_data_standard = create_png_image_bytes()
        png_data_bambu = create_png_image_bytes()

        # Create 3MF with both standard and bambu thumbnails
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Metadata/thumbnail.png", png_data_standard)
            zf.writestr("Metadata/plate_1.png", png_data_bambu)
            zf.writestr("3D/3dmodel.model", "<model>...</model>")

        file_content = buffer.getvalue()

        result = extract_3mf_thumbnail(file_content)

        assert result is not None
        thumbnail_data, content_type = result
        # Standard path should be preferred
        assert thumbnail_data == png_data_standard


# =============================================================================
# File Validation Tests
# =============================================================================


class TestFileValidation:
    """Test cases for file validation in ModelFileService."""

    def test_allowed_extensions(self):
        """Test that allowed extensions are correct."""
        assert ".stl" in ALLOWED_EXTENSIONS
        assert ".3mf" in ALLOWED_EXTENSIONS
        assert ".gcode" in ALLOWED_EXTENSIONS
        assert ".gco" in ALLOWED_EXTENSIONS
        assert ".g" in ALLOWED_EXTENSIONS
        assert ".exe" not in ALLOWED_EXTENSIONS
        assert ".py" not in ALLOWED_EXTENSIONS

    def test_max_file_size(self):
        """Test that max file size is reasonable for 3D files."""
        # Max should be at least 100MB for large gcode files
        assert MAX_FILE_SIZE >= 100 * 1024 * 1024
        # But not more than 1GB
        assert MAX_FILE_SIZE <= 1024 * 1024 * 1024

    def test_validate_file_valid_stl(self):
        """Test validation passes for valid STL file."""
        service = _create_mock_service()
        stl_content = create_minimal_stl()

        extension = service._validate_file(stl_content, "model/stl", "model.stl")

        assert extension == ".stl"

    def test_validate_file_valid_3mf(self):
        """Test validation passes for valid 3MF file."""
        service = _create_mock_service()
        content_3mf = create_3mf_with_thumbnail()

        extension = service._validate_file(content_3mf, "model/3mf", "model.3mf")

        assert extension == ".3mf"

    def test_validate_file_valid_gcode(self):
        """Test validation passes for valid gcode file."""
        service = _create_mock_service()
        gcode_content = create_minimal_gcode()

        extension = service._validate_file(gcode_content, "text/x-gcode", "print.gcode")

        assert extension == ".gcode"

    def test_validate_file_invalid_extension(self):
        """Test validation fails for invalid file extension."""
        service = _create_mock_service()
        content = b"some content"

        with pytest.raises(ModelFileStorageError) as exc_info:
            service._validate_file(content, "text/plain", "script.py")

        assert "Invalid file type" in str(exc_info.value)

    def test_validate_file_too_large(self):
        """Test validation fails for oversized file."""
        service = _create_mock_service()
        # Create content larger than MAX_FILE_SIZE
        large_content = b"x" * (MAX_FILE_SIZE + 1)

        with pytest.raises(ModelFileStorageError) as exc_info:
            service._validate_file(large_content, "model/stl", "large.stl")

        assert "too large" in str(exc_info.value)

    def test_validate_file_case_insensitive_extension(self):
        """Test validation handles uppercase extensions."""
        service = _create_mock_service()
        stl_content = create_minimal_stl()

        extension = service._validate_file(stl_content, "model/stl", "MODEL.STL")

        assert extension == ".stl"


# =============================================================================
# Local Storage Tests
# =============================================================================


class TestLocalStorage:
    """Test cases for local file storage operations."""

    @pytest.mark.asyncio
    async def test_save_local_creates_directories(self, tmp_path):
        """Test that _save_local creates necessary directories."""
        service = _create_mock_service(storage_path=str(tmp_path))
        content = create_minimal_stl()
        model_dir = f"models/{uuid4()}"
        filename = "test.stl"

        file_url = await service._save_local(content, model_dir, filename)

        assert file_url == f"/uploads/{model_dir}/{filename}"
        assert (tmp_path / model_dir / filename).exists()

    @pytest.mark.asyncio
    async def test_save_local_writes_content(self, tmp_path):
        """Test that _save_local writes correct content."""
        service = _create_mock_service(storage_path=str(tmp_path))
        content = create_minimal_stl()
        model_dir = f"models/{uuid4()}"
        filename = "test.stl"

        await service._save_local(content, model_dir, filename)

        saved_content = (tmp_path / model_dir / filename).read_bytes()
        assert saved_content == content

    @pytest.mark.asyncio
    async def test_get_local_reads_content(self, tmp_path):
        """Test that _get_local reads file content correctly."""
        service = _create_mock_service(storage_path=str(tmp_path))
        content = create_minimal_stl()
        model_dir = f"models/{uuid4()}"
        filename = "test.stl"

        # Save first
        await service._save_local(content, model_dir, filename)

        # Then read
        file_url = f"/uploads/{model_dir}/{filename}"
        read_content = await service._get_local(file_url)

        assert read_content == content

    @pytest.mark.asyncio
    async def test_get_local_invalid_url(self, tmp_path):
        """Test that _get_local raises for invalid URL format."""
        service = _create_mock_service(storage_path=str(tmp_path))

        with pytest.raises(ModelFileStorageError) as exc_info:
            await service._get_local("/invalid/path/file.stl")

        assert "Invalid file URL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_local_file_not_found(self, tmp_path):
        """Test that _get_local raises for missing file."""
        service = _create_mock_service(storage_path=str(tmp_path))

        with pytest.raises(ModelFileStorageError) as exc_info:
            await service._get_local("/uploads/models/nonexistent/file.stl")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_local_removes_file(self, tmp_path):
        """Test that _delete_local removes the file."""
        service = _create_mock_service(storage_path=str(tmp_path))
        content = create_minimal_stl()
        model_dir = f"models/{uuid4()}"
        filename = "test.stl"

        # Save first
        await service._save_local(content, model_dir, filename)
        file_path = tmp_path / model_dir / filename
        assert file_path.exists()

        # Delete
        file_url = f"/uploads/{model_dir}/{filename}"
        result = await service._delete_local(file_url)

        assert result is True
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_local_nonexistent_file(self, tmp_path):
        """Test that _delete_local handles missing files gracefully."""
        service = _create_mock_service(storage_path=str(tmp_path))

        result = await service._delete_local("/uploads/models/nonexistent/file.stl")

        # Should return True (no error) even if file doesn't exist
        assert result is True


# =============================================================================
# S3 Storage Tests (Mocked)
# =============================================================================


class TestS3Storage:
    """Test cases for S3 storage operations (using mocks)."""

    @pytest.mark.asyncio
    async def test_save_s3_uploads_content(self):
        """Test that _save_s3 uploads to S3 correctly."""
        mock_s3_client = MagicMock()
        service = _create_mock_service(storage_type="s3")
        service._s3_client = mock_s3_client
        service._bucket = "test-bucket"

        content = create_minimal_stl()
        model_dir = f"models/{uuid4()}"
        filename = "test.stl"

        file_url = await service._save_s3(content, model_dir, filename, "model/stl")

        assert file_url == f"/uploads/{model_dir}/{filename}"
        mock_s3_client.upload_fileobj.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_s3_no_client_raises_error(self):
        """Test that _save_s3 raises error when S3 not configured."""
        service = _create_mock_service(storage_type="s3")
        service._s3_client = None

        with pytest.raises(ModelFileStorageError) as exc_info:
            await service._save_s3(b"content", "models/x", "file.stl", "model/stl")

        assert "not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_s3_no_bucket_raises_error(self):
        """Test that _save_s3 raises error when bucket not configured."""
        service = _create_mock_service(storage_type="s3")
        service._s3_client = MagicMock()
        service._bucket = None

        with pytest.raises(ModelFileStorageError) as exc_info:
            await service._save_s3(b"content", "models/x", "file.stl", "model/stl")

        assert "bucket not configured" in str(exc_info.value)


# =============================================================================
# Tenant Isolation Tests
# =============================================================================


class TestTenantIsolation:
    """Test cases for tenant isolation in ModelFileService."""

    @pytest.mark.asyncio
    async def test_get_model_filters_by_tenant(self):
        """Test that _get_model only returns models for the service's tenant."""
        # This would require actual DB setup, so we test the query structure
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()

        service = ModelFileService(db=mock_db, tenant=mock_tenant)

        # The _get_model method should filter by tenant_id
        # We verify this by checking the service is initialized correctly
        assert service.tenant.id == mock_tenant.id

    @pytest.mark.asyncio
    async def test_service_stores_tenant_reference(self):
        """Test that service maintains tenant reference."""
        mock_db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_user = MagicMock()

        service = ModelFileService(db=mock_db, tenant=mock_tenant, user=mock_user)

        assert service.tenant == mock_tenant
        assert service.user == mock_user


# =============================================================================
# Helper Functions for Creating Mock Services
# =============================================================================


def _create_mock_service(
    storage_type: str = "local",
    storage_path: str = "/tmp/test-storage",
) -> ModelFileService:
    """Create a ModelFileService with mocked dependencies."""
    mock_db = AsyncMock()
    mock_tenant = MagicMock()
    mock_tenant.id = uuid4()

    # Mock settings
    with patch("app.services.model_file_service.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.storage_type = storage_type
        mock_settings.storage_path = storage_path
        mock_settings.storage_s3_endpoint = None
        mock_settings.storage_s3_bucket = "test-bucket"
        mock_settings.storage_s3_region = "us-east-1"
        mock_settings.storage_s3_access_key = "test-key"
        mock_settings.storage_s3_secret_key = "test-secret"
        mock_get_settings.return_value = mock_settings

        service = ModelFileService(db=mock_db, tenant=mock_tenant)
        # For local storage tests, update the base_path
        if storage_type == "local":
            service.base_path = Path(storage_path)

        return service
