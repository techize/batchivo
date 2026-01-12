"""
Tests for image storage service.

Tests both local filesystem and S3/MinIO storage backends.
"""

import os
import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock
from PIL import Image
import boto3
from botocore.exceptions import ClientError
from moto import mock_aws

from app.services.image_storage import (
    ImageStorage,
    ImageStorageError,
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE,
)


# Test bucket name for S3 tests
TEST_BUCKET = "batchivo-test-images"


def create_test_image(width: int = 100, height: int = 100, format: str = "JPEG") -> bytes:
    """Create a test image in memory."""
    mode = "RGBA" if format == "PNG" else "RGB"
    img = Image.new(mode, (width, height), color="red")
    buffer = BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


@pytest.fixture
def local_storage(tmp_path):
    """Create a local storage instance."""
    storage = ImageStorage()
    storage.base_path = tmp_path
    storage.storage_type = "local"
    (tmp_path / "products").mkdir(exist_ok=True)
    return storage


@pytest.fixture
def s3_storage(tmp_path):
    """Create an S3 storage instance with mocked AWS."""
    with mock_aws():
        # Create the bucket
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=TEST_BUCKET)

        # Create storage instance
        storage = ImageStorage()
        storage.storage_type = "s3"
        storage._bucket = TEST_BUCKET
        storage._s3_client = conn

        yield storage


@pytest.fixture(params=["local", "s3"])
def storage(request, tmp_path):
    """Parameterized fixture that provides both local and S3 storage."""
    if request.param == "local":
        storage = ImageStorage()
        storage.base_path = tmp_path
        storage.storage_type = "local"
        (tmp_path / "products").mkdir(exist_ok=True)
        yield storage
    else:
        with mock_aws():
            conn = boto3.client("s3", region_name="us-east-1")
            conn.create_bucket(Bucket=TEST_BUCKET)

            storage = ImageStorage()
            storage.storage_type = "s3"
            storage._bucket = TEST_BUCKET
            storage._s3_client = conn

            yield storage


class TestImageStorageConstants:
    """Tests for image storage constants."""

    def test_allowed_content_types(self):
        """Test allowed content types are defined."""
        assert "image/jpeg" in ALLOWED_CONTENT_TYPES
        assert "image/png" in ALLOWED_CONTENT_TYPES
        assert "image/webp" in ALLOWED_CONTENT_TYPES
        assert len(ALLOWED_CONTENT_TYPES) == 3

    def test_max_file_size(self):
        """Test max file size is 10MB."""
        assert MAX_FILE_SIZE == 10 * 1024 * 1024


class TestImageStorageValidation:
    """Tests for image validation - applies to both storage types."""

    @pytest.mark.asyncio
    async def test_save_image_invalid_content_type(self, storage):
        """Test saving image with invalid content type."""
        content = create_test_image()

        with pytest.raises(ImageStorageError, match="Invalid file type"):
            await storage.save_image(
                file_content=content,
                content_type="image/gif",  # Not allowed
                product_id="test-product-id",
            )

    @pytest.mark.asyncio
    async def test_save_image_too_large(self, storage):
        """Test saving image that's too large."""
        # Create content larger than MAX_FILE_SIZE
        large_content = b"x" * (MAX_FILE_SIZE + 1)

        with pytest.raises(ImageStorageError, match="File too large"):
            await storage.save_image(
                file_content=large_content,
                content_type="image/jpeg",
                product_id="test-product-id",
            )

    @pytest.mark.asyncio
    async def test_save_image_invalid_image_data(self, storage):
        """Test saving invalid image data."""
        content = b"not an image"

        with pytest.raises(ImageStorageError, match="Invalid image file"):
            await storage.save_image(
                file_content=content,
                content_type="image/jpeg",
                product_id="test-product-id",
            )


class TestImageStorageSave:
    """Tests for saving images - both storage types."""

    @pytest.mark.asyncio
    async def test_save_image_success_jpeg(self, storage):
        """Test successfully saving a JPEG image."""
        content = create_test_image(format="JPEG")

        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="test-product-123",
            original_filename="test.jpg",
        )

        assert "image_url" in result
        assert "thumbnail_url" in result
        assert result["content_type"] == "image/jpeg"
        assert result["file_size"] == len(content)
        assert "/uploads/products/test-product-123/" in result["image_url"]
        assert "_thumb" in result["thumbnail_url"]

    @pytest.mark.asyncio
    async def test_save_image_success_png(self, storage):
        """Test successfully saving a PNG image."""
        content = create_test_image(format="PNG")

        result = await storage.save_image(
            file_content=content,
            content_type="image/png",
            product_id="test-product-456",
        )

        assert result["content_type"] == "image/png"
        assert ".png" in result["image_url"]

    @pytest.mark.asyncio
    async def test_save_image_success_webp(self, storage):
        """Test successfully saving a WebP image."""
        content = create_test_image(format="WEBP")

        result = await storage.save_image(
            file_content=content,
            content_type="image/webp",
            product_id="test-product-789",
        )

        assert result["content_type"] == "image/webp"
        assert ".webp" in result["image_url"]


class TestImageStorageDelete:
    """Tests for deleting images - both storage types."""

    @pytest.mark.asyncio
    async def test_delete_image(self, storage):
        """Test deleting an image."""
        # First save an image
        content = create_test_image()
        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="delete-test",
        )

        # Then delete it
        delete_result = await storage.delete_image(
            result["image_url"],
            result["thumbnail_url"],
        )

        assert delete_result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_image(self, storage):
        """Test deleting a non-existent image doesn't fail."""
        result = await storage.delete_image(
            "/uploads/products/nonexistent/image.jpg",
            "/uploads/products/nonexistent/thumb.jpg",
        )

        # Should return True even if files don't exist (for local)
        # S3 also doesn't error on delete of nonexistent keys
        assert result is True


class TestImageStorageGet:
    """Tests for retrieving images - both storage types."""

    @pytest.mark.asyncio
    async def test_get_image(self, storage):
        """Test getting an image."""
        # First save an image
        content = create_test_image()
        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="get-test",
        )

        # Then get it
        image_bytes, content_type = await storage.get_image(result["image_url"])

        assert len(image_bytes) > 0
        assert content_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_get_image_not_found(self, storage):
        """Test getting a non-existent image raises error."""
        with pytest.raises(ImageStorageError, match="Image not found|not found"):
            await storage.get_image("/uploads/products/nonexistent/image.jpg")

    @pytest.mark.asyncio
    async def test_get_image_invalid_url(self, storage):
        """Test getting with invalid URL raises error."""
        with pytest.raises(ImageStorageError, match="Invalid image URL"):
            await storage.get_image("not-a-valid-url")


class TestImageStorageResizing:
    """Tests for image resizing functionality."""

    @pytest.mark.asyncio
    async def test_large_image_resized(self, storage):
        """Test that large images are resized."""
        # Create a large image (1200x1200)
        content = create_test_image(width=1200, height=1200, format="JPEG")

        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="large-test",
        )

        # Verify the display image was created
        assert result["image_url"] is not None

        # Get the saved image and check dimensions
        image_bytes, _ = await storage.get_image(result["image_url"])
        saved_img = Image.open(BytesIO(image_bytes))
        assert saved_img.width <= 800
        assert saved_img.height <= 800

    @pytest.mark.asyncio
    async def test_thumbnail_created(self, storage):
        """Test that thumbnail is created."""
        content = create_test_image(width=500, height=500, format="JPEG")

        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="thumb-test",
        )

        # Get the thumbnail and check dimensions
        thumb_bytes, _ = await storage.get_image(result["thumbnail_url"])
        thumb_img = Image.open(BytesIO(thumb_bytes))
        assert thumb_img.width <= 300
        assert thumb_img.height <= 300


class TestImageStorageRotation:
    """Tests for image rotation functionality."""

    @pytest.mark.asyncio
    async def test_rotate_image_90_degrees(self, storage):
        """Test rotating an image 90 degrees clockwise."""
        # Create a non-square image (wider than tall)
        content = create_test_image(width=200, height=100, format="JPEG")

        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="rotate-test",
        )

        # Rotate 90 degrees
        rotate_result = await storage.rotate_image(
            result["image_url"],
            result["thumbnail_url"],
            90,
        )

        assert rotate_result is True

        # After 90 degree rotation, dimensions should be swapped
        image_bytes, _ = await storage.get_image(result["image_url"])
        rotated_img = Image.open(BytesIO(image_bytes))
        # The rotated image should be taller than wide (100x200 -> 200x100 rotated is taller)
        assert rotated_img.height > rotated_img.width

    @pytest.mark.asyncio
    async def test_rotate_image_180_degrees(self, storage):
        """Test rotating an image 180 degrees."""
        content = create_test_image(width=200, height=100, format="JPEG")

        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="rotate-180",
        )

        rotate_result = await storage.rotate_image(
            result["image_url"],
            None,  # No thumbnail
            180,
        )

        assert rotate_result is True

        # After 180 degree rotation, dimensions stay the same
        image_bytes, _ = await storage.get_image(result["image_url"])
        rotated_img = Image.open(BytesIO(image_bytes))
        assert rotated_img.width > rotated_img.height

    @pytest.mark.asyncio
    async def test_rotate_image_270_degrees(self, storage):
        """Test rotating an image 270 degrees clockwise."""
        content = create_test_image(width=200, height=100, format="JPEG")

        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="rotate-270",
        )

        rotate_result = await storage.rotate_image(
            result["image_url"],
            None,
            270,
        )

        assert rotate_result is True

        # After 270 degree rotation, dimensions should be swapped
        image_bytes, _ = await storage.get_image(result["image_url"])
        rotated_img = Image.open(BytesIO(image_bytes))
        assert rotated_img.height > rotated_img.width

    @pytest.mark.asyncio
    async def test_rotate_image_invalid_degrees(self, storage):
        """Test rotating with invalid degrees raises error."""
        content = create_test_image()

        result = await storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="rotate-invalid",
        )

        with pytest.raises(ImageStorageError, match="Invalid rotation"):
            await storage.rotate_image(
                result["image_url"],
                None,
                45,  # Invalid - not 90, 180, or 270
            )


class TestS3SpecificErrors:
    """Tests for S3-specific error scenarios."""

    @pytest.mark.asyncio
    async def test_s3_connection_failure(self, tmp_path):
        """Test handling S3 connection failures."""
        storage = ImageStorage()
        storage.storage_type = "s3"
        storage._bucket = TEST_BUCKET

        # Create a mock client that raises connection error
        mock_client = MagicMock()
        mock_client.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "Service unavailable"}},
            "PutObject",
        )
        storage._s3_client = mock_client

        content = create_test_image()

        with pytest.raises(ImageStorageError, match="Failed to upload to S3"):
            await storage.save_image(
                file_content=content,
                content_type="image/jpeg",
                product_id="s3-error-test",
            )

    @pytest.mark.asyncio
    async def test_s3_bucket_not_found(self, tmp_path):
        """Test handling bucket not found error."""
        with mock_aws():
            # Create client but don't create bucket
            conn = boto3.client("s3", region_name="us-east-1")

            storage = ImageStorage()
            storage.storage_type = "s3"
            storage._bucket = "nonexistent-bucket"
            storage._s3_client = conn

            content = create_test_image()

            with pytest.raises(ImageStorageError, match="Failed to upload to S3"):
                await storage.save_image(
                    file_content=content,
                    content_type="image/jpeg",
                    product_id="bucket-error-test",
                )

    @pytest.mark.asyncio
    async def test_s3_access_denied(self, tmp_path):
        """Test handling access denied error."""
        storage = ImageStorage()
        storage.storage_type = "s3"
        storage._bucket = TEST_BUCKET

        # Create a mock client that raises access denied
        mock_client = MagicMock()
        mock_client.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )
        storage._s3_client = mock_client

        content = create_test_image()

        with pytest.raises(ImageStorageError, match="Failed to upload to S3"):
            await storage.save_image(
                file_content=content,
                content_type="image/jpeg",
                product_id="access-denied-test",
            )

    @pytest.mark.asyncio
    async def test_s3_get_image_not_found(self):
        """Test S3 returns proper error for non-existent image."""
        with mock_aws():
            conn = boto3.client("s3", region_name="us-east-1")
            conn.create_bucket(Bucket=TEST_BUCKET)

            storage = ImageStorage()
            storage.storage_type = "s3"
            storage._bucket = TEST_BUCKET
            storage._s3_client = conn

            with pytest.raises(ImageStorageError, match="Image not found"):
                await storage.get_image("/uploads/products/nonexistent/image.jpg")

    @pytest.mark.asyncio
    async def test_s3_delete_returns_true_for_nonexistent(self):
        """Test S3 delete returns True for non-existent keys (S3 behavior)."""
        with mock_aws():
            conn = boto3.client("s3", region_name="us-east-1")
            conn.create_bucket(Bucket=TEST_BUCKET)

            storage = ImageStorage()
            storage.storage_type = "s3"
            storage._bucket = TEST_BUCKET
            storage._s3_client = conn

            result = await storage.delete_image(
                "/uploads/products/nonexistent/image.jpg",
                "/uploads/products/nonexistent/thumb.jpg",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_s3_rotate_image_not_found(self):
        """Test S3 rotate returns proper error for non-existent image."""
        with mock_aws():
            conn = boto3.client("s3", region_name="us-east-1")
            conn.create_bucket(Bucket=TEST_BUCKET)

            storage = ImageStorage()
            storage.storage_type = "s3"
            storage._bucket = TEST_BUCKET
            storage._s3_client = conn

            with pytest.raises(ImageStorageError, match="Failed to rotate"):
                await storage.rotate_image(
                    "/uploads/products/nonexistent/image.jpg",
                    None,
                    90,
                )


class TestLocalStorageSpecific:
    """Tests specific to local storage."""

    @pytest.mark.asyncio
    async def test_local_creates_product_directory(self, local_storage, tmp_path):
        """Test that local storage creates product directory."""
        content = create_test_image()

        await local_storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="new-product",
        )

        # Verify directory was created
        product_dir = tmp_path / "products" / "new-product"
        assert product_dir.exists()

    @pytest.mark.asyncio
    async def test_local_file_exists_after_save(self, local_storage, tmp_path):
        """Test that files exist after saving."""
        content = create_test_image()

        result = await local_storage.save_image(
            file_content=content,
            content_type="image/jpeg",
            product_id="file-test",
        )

        # Check files exist
        image_path = tmp_path / result["image_url"][9:]  # Remove /uploads/
        thumb_path = tmp_path / result["thumbnail_url"][9:]

        assert image_path.exists()
        assert thumb_path.exists()


class TestConcurrentUploads:
    """Tests for concurrent upload scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_uploads_same_product(self, storage):
        """Test uploading multiple images to same product."""
        import asyncio

        product_id = "concurrent-test"
        content1 = create_test_image(width=100, height=100)
        content2 = create_test_image(width=150, height=150)
        content3 = create_test_image(width=200, height=200)

        # Upload multiple images concurrently
        results = await asyncio.gather(
            storage.save_image(content1, "image/jpeg", product_id),
            storage.save_image(content2, "image/jpeg", product_id),
            storage.save_image(content3, "image/jpeg", product_id),
        )

        # All should succeed with unique URLs
        urls = [r["image_url"] for r in results]
        assert len(set(urls)) == 3  # All unique


class TestStorageTypeFromEnvironment:
    """Tests for storage type configuration."""

    def test_storage_type_defaults_to_local(self):
        """Test storage type defaults to local when not configured."""
        with patch.dict(os.environ, {"STORAGE_TYPE": "local"}, clear=False):
            # Would need to test actual settings behavior
            pass

    def test_storage_type_can_be_s3(self):
        """Test storage type can be set to s3."""
        with patch.dict(os.environ, {"STORAGE_TYPE": "s3"}, clear=False):
            # Would need to test actual settings behavior
            pass
