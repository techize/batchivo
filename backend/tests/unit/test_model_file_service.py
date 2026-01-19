"""
Tests for model file service.

Includes tests for 3MF thumbnail extraction.
"""

import io
import zipfile
import pytest

from app.services.model_file_service import extract_3mf_thumbnail


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
    # Minimal valid PNG: 1x1 red pixel
    from PIL import Image
    import io

    img = Image.new("RGB", (1, 1), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_jpeg_image_bytes() -> bytes:
    """Create valid JPEG image bytes (minimal 1x1 red pixel JPEG)."""
    from PIL import Image
    import io

    img = Image.new("RGB", (1, 1), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


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
