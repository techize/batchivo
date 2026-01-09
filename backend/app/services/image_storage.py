"""
Image storage service for product images.

Supports local filesystem storage and S3/MinIO storage.
"""

import logging
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from PIL import Image

from app.config import get_settings

logger = logging.getLogger(__name__)

# Allowed image types
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Image size limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
THUMBNAIL_SIZE = (300, 300)
DISPLAY_SIZE = (800, 800)


class ImageStorageError(Exception):
    """Error during image storage operation."""

    pass


class ImageStorage:
    """
    Image storage service for product images.

    Supports:
    - Local filesystem storage (development)
    - S3/MinIO storage (production)
    """

    def __init__(self):
        self.settings = get_settings()
        self.storage_type = self.settings.storage_type
        self.base_path = Path(self.settings.storage_path)

        # Ensure local storage directory exists
        if self.storage_type == "local":
            self.base_path.mkdir(parents=True, exist_ok=True)
            (self.base_path / "products").mkdir(exist_ok=True)

        # Initialize S3 client if using S3 storage
        self._s3_client = None
        if self.storage_type == "s3":
            self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3/MinIO client."""
        s3_config = {}

        # Use custom endpoint for MinIO
        if self.settings.storage_s3_endpoint:
            s3_config["endpoint_url"] = self.settings.storage_s3_endpoint

        self._s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.settings.storage_s3_access_key,
            aws_secret_access_key=self.settings.storage_s3_secret_key,
            region_name=self.settings.storage_s3_region,
            **s3_config,
        )
        self._bucket = self.settings.storage_s3_bucket

    async def save_image(
        self,
        file_content: bytes,
        content_type: str,
        product_id: str,
        original_filename: Optional[str] = None,
    ) -> dict:
        """
        Save an image and generate thumbnail.

        Args:
            file_content: Raw image bytes
            content_type: MIME type of the image
            product_id: UUID of the product
            original_filename: Original filename for reference

        Returns:
            dict with:
            - image_url: URL/path to the main image
            - thumbnail_url: URL/path to the thumbnail
            - file_size: Size in bytes
            - content_type: MIME type

        Raises:
            ImageStorageError: If validation or save fails
        """
        # Validate content type
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ImageStorageError(
                f"Invalid file type: {content_type}. Allowed: {', '.join(ALLOWED_CONTENT_TYPES.keys())}"
            )

        # Validate file size
        if len(file_content) > MAX_FILE_SIZE:
            raise ImageStorageError(
                f"File too large: {len(file_content)} bytes. Maximum: {MAX_FILE_SIZE} bytes"
            )

        # Validate it's actually an image
        try:
            img = Image.open(BytesIO(file_content))
            img.verify()
            # Reopen for processing (verify closes the file)
            img = Image.open(BytesIO(file_content))
        except Exception as e:
            raise ImageStorageError(f"Invalid image file: {e}")

        # Generate unique filename
        extension = ALLOWED_CONTENT_TYPES[content_type]
        image_id = str(uuid.uuid4())
        filename = f"{image_id}{extension}"
        thumbnail_filename = f"{image_id}_thumb{extension}"

        # Create product directory
        product_dir = f"products/{product_id}"

        if self.storage_type == "local":
            return await self._save_local(
                img, file_content, product_dir, filename, thumbnail_filename, content_type
            )
        else:
            return await self._save_s3(
                img, file_content, product_dir, filename, thumbnail_filename, content_type
            )

    async def _save_local(
        self,
        img: Image.Image,
        original_content: bytes,
        product_dir: str,
        filename: str,
        thumbnail_filename: str,
        content_type: str,
    ) -> dict:
        """Save image to local filesystem."""
        # Create product directory
        full_dir = self.base_path / product_dir
        full_dir.mkdir(parents=True, exist_ok=True)

        # Resize for display (if larger than DISPLAY_SIZE)
        display_img = img.copy()
        display_img.thumbnail(DISPLAY_SIZE, Image.Resampling.LANCZOS)

        # Convert to RGB if necessary (for JPEG)
        if content_type == "image/jpeg" and display_img.mode in ("RGBA", "P"):
            display_img = display_img.convert("RGB")

        # Save display image
        display_path = full_dir / filename
        save_format = (
            "JPEG"
            if content_type == "image/jpeg"
            else "PNG"
            if content_type == "image/png"
            else "WEBP"
        )
        display_img.save(display_path, format=save_format, quality=85, optimize=True)

        # Create and save thumbnail
        thumb_img = img.copy()
        thumb_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        if content_type == "image/jpeg" and thumb_img.mode in ("RGBA", "P"):
            thumb_img = thumb_img.convert("RGB")
        thumb_path = full_dir / thumbnail_filename
        thumb_img.save(thumb_path, format=save_format, quality=80, optimize=True)

        # Generate URLs (relative paths for local storage)
        image_url = f"/uploads/{product_dir}/{filename}"
        thumbnail_url = f"/uploads/{product_dir}/{thumbnail_filename}"

        return {
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "file_size": len(original_content),
            "content_type": content_type,
        }

    async def _save_s3(
        self,
        img: Image.Image,
        original_content: bytes,
        product_dir: str,
        filename: str,
        thumbnail_filename: str,
        content_type: str,
    ) -> dict:
        """Save image to S3/MinIO storage."""
        try:
            # Resize for display (if larger than DISPLAY_SIZE)
            display_img = img.copy()
            display_img.thumbnail(DISPLAY_SIZE, Image.Resampling.LANCZOS)

            # Convert to RGB if necessary (for JPEG)
            if content_type == "image/jpeg" and display_img.mode in ("RGBA", "P"):
                display_img = display_img.convert("RGB")

            # Determine save format
            save_format = (
                "JPEG"
                if content_type == "image/jpeg"
                else "PNG"
                if content_type == "image/png"
                else "WEBP"
            )

            # Save display image to bytes
            display_buffer = BytesIO()
            display_img.save(display_buffer, format=save_format, quality=85, optimize=True)
            display_buffer.seek(0)

            # Create and save thumbnail to bytes
            thumb_img = img.copy()
            thumb_img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            if content_type == "image/jpeg" and thumb_img.mode in ("RGBA", "P"):
                thumb_img = thumb_img.convert("RGB")
            thumb_buffer = BytesIO()
            thumb_img.save(thumb_buffer, format=save_format, quality=80, optimize=True)
            thumb_buffer.seek(0)

            # S3 keys (paths within bucket)
            image_key = f"{product_dir}/{filename}"
            thumbnail_key = f"{product_dir}/{thumbnail_filename}"

            # Upload to S3
            self._s3_client.upload_fileobj(
                display_buffer,
                self._bucket,
                image_key,
                ExtraArgs={"ContentType": content_type},
            )
            self._s3_client.upload_fileobj(
                thumb_buffer,
                self._bucket,
                thumbnail_key,
                ExtraArgs={"ContentType": content_type},
            )

            # Generate URLs (using /uploads/ prefix for backend proxy)
            image_url = f"/uploads/{image_key}"
            thumbnail_url = f"/uploads/{thumbnail_key}"

            return {
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "file_size": len(original_content),
                "content_type": content_type,
            }
        except ClientError as e:
            raise ImageStorageError(f"Failed to upload to S3: {e}")

    async def delete_image(self, image_url: str, thumbnail_url: Optional[str] = None) -> bool:
        """
        Delete an image and its thumbnail.

        Args:
            image_url: URL/path to the main image
            thumbnail_url: URL/path to the thumbnail

        Returns:
            True if deleted successfully
        """
        if self.storage_type == "local":
            return await self._delete_local(image_url, thumbnail_url)
        else:
            return await self._delete_s3(image_url, thumbnail_url)

    async def _delete_local(self, image_url: str, thumbnail_url: Optional[str] = None) -> bool:
        """Delete image from local filesystem."""
        try:
            # Convert URL to file path
            if image_url.startswith("/uploads/"):
                image_path = self.base_path / image_url[9:]  # Remove /uploads/ prefix
                if image_path.exists():
                    image_path.unlink()

            if thumbnail_url and thumbnail_url.startswith("/uploads/"):
                thumb_path = self.base_path / thumbnail_url[9:]
                if thumb_path.exists():
                    thumb_path.unlink()

            return True
        except Exception:
            return False

    async def _delete_s3(self, image_url: str, thumbnail_url: Optional[str] = None) -> bool:
        """Delete image from S3/MinIO storage."""
        try:
            # Convert URL to S3 key
            if image_url.startswith("/uploads/"):
                image_key = image_url[9:]  # Remove /uploads/ prefix
                self._s3_client.delete_object(Bucket=self._bucket, Key=image_key)

            if thumbnail_url and thumbnail_url.startswith("/uploads/"):
                thumb_key = thumbnail_url[9:]
                self._s3_client.delete_object(Bucket=self._bucket, Key=thumb_key)

            return True
        except ClientError:
            return False

    async def rotate_image(
        self, image_url: str, thumbnail_url: Optional[str], degrees: int = 90
    ) -> bool:
        """
        Rotate an image and its thumbnail.

        Args:
            image_url: URL/path to the main image
            thumbnail_url: URL/path to the thumbnail
            degrees: Rotation degrees (90, 180, 270). Positive = clockwise.

        Returns:
            True if rotated successfully
        """
        if self.storage_type == "local":
            return await self._rotate_local(image_url, thumbnail_url, degrees)
        else:
            return await self._rotate_s3(image_url, thumbnail_url, degrees)

    async def _rotate_local(
        self, image_url: str, thumbnail_url: Optional[str], degrees: int
    ) -> bool:
        """Rotate image on local filesystem."""
        try:
            # Normalize degrees to 90, 180, or 270
            degrees = degrees % 360
            if degrees not in (90, 180, 270):
                raise ImageStorageError(f"Invalid rotation: {degrees}. Use 90, 180, or 270.")

            # PIL uses counter-clockwise, so negate for clockwise rotation
            pil_degrees = -degrees

            # Rotate main image
            if image_url.startswith("/uploads/"):
                image_path = self.base_path / image_url[9:]
                if image_path.exists():
                    with Image.open(image_path) as img:
                        rotated = img.rotate(pil_degrees, expand=True)
                        # Determine format from extension
                        ext = image_path.suffix.lower()
                        save_format = (
                            "JPEG"
                            if ext in (".jpg", ".jpeg")
                            else "PNG"
                            if ext == ".png"
                            else "WEBP"
                        )
                        if save_format == "JPEG" and rotated.mode in ("RGBA", "P"):
                            rotated = rotated.convert("RGB")
                        rotated.save(image_path, format=save_format, quality=85, optimize=True)

            # Rotate thumbnail
            if thumbnail_url and thumbnail_url.startswith("/uploads/"):
                thumb_path = self.base_path / thumbnail_url[9:]
                if thumb_path.exists():
                    with Image.open(thumb_path) as img:
                        rotated = img.rotate(pil_degrees, expand=True)
                        ext = thumb_path.suffix.lower()
                        save_format = (
                            "JPEG"
                            if ext in (".jpg", ".jpeg")
                            else "PNG"
                            if ext == ".png"
                            else "WEBP"
                        )
                        if save_format == "JPEG" and rotated.mode in ("RGBA", "P"):
                            rotated = rotated.convert("RGB")
                        rotated.save(thumb_path, format=save_format, quality=80, optimize=True)

            return True
        except Exception as e:
            raise ImageStorageError(f"Failed to rotate image: {e}")

    async def _rotate_s3(self, image_url: str, thumbnail_url: Optional[str], degrees: int) -> bool:
        """Rotate image in S3/MinIO storage."""
        try:
            logger.debug(f"_rotate_s3: Starting rotation of {image_url} by {degrees} degrees")
            # Normalize degrees to 90, 180, or 270
            degrees = degrees % 360
            if degrees not in (90, 180, 270):
                raise ImageStorageError(f"Invalid rotation: {degrees}. Use 90, 180, or 270.")

            # PIL uses counter-clockwise, so negate for clockwise rotation
            pil_degrees = -degrees

            # Rotate main image
            if image_url.startswith("/uploads/"):
                image_key = image_url[9:]
                # Download image
                response = self._s3_client.get_object(Bucket=self._bucket, Key=image_key)
                image_data = response["Body"].read()
                content_type = response.get("ContentType", "image/jpeg")

                # Rotate
                with Image.open(BytesIO(image_data)) as img:
                    rotated = img.rotate(pil_degrees, expand=True)
                    ext = image_key.split(".")[-1].lower()
                    save_format = (
                        "JPEG" if ext in ("jpg", "jpeg") else "PNG" if ext == "png" else "WEBP"
                    )
                    if save_format == "JPEG" and rotated.mode in ("RGBA", "P"):
                        rotated = rotated.convert("RGB")

                    # Save to buffer and re-upload (use high quality to minimize loss)
                    buffer = BytesIO()
                    rotated.save(buffer, format=save_format, quality=95, optimize=True)
                    buffer.seek(0)
                    logger.debug(
                        f"_rotate_s3: Uploading rotated image {image_key}, size={rotated.width}x{rotated.height}"
                    )
                    self._s3_client.upload_fileobj(
                        buffer,
                        self._bucket,
                        image_key,
                        ExtraArgs={"ContentType": content_type},
                    )
                    logger.debug(f"_rotate_s3: Upload complete for {image_key}")

            # Rotate thumbnail
            if thumbnail_url and thumbnail_url.startswith("/uploads/"):
                thumb_key = thumbnail_url[9:]
                response = self._s3_client.get_object(Bucket=self._bucket, Key=thumb_key)
                thumb_data = response["Body"].read()
                content_type = response.get("ContentType", "image/jpeg")

                with Image.open(BytesIO(thumb_data)) as img:
                    rotated = img.rotate(pil_degrees, expand=True)
                    ext = thumb_key.split(".")[-1].lower()
                    save_format = (
                        "JPEG" if ext in ("jpg", "jpeg") else "PNG" if ext == "png" else "WEBP"
                    )
                    if save_format == "JPEG" and rotated.mode in ("RGBA", "P"):
                        rotated = rotated.convert("RGB")

                    buffer = BytesIO()
                    rotated.save(buffer, format=save_format, quality=90, optimize=True)
                    buffer.seek(0)
                    self._s3_client.upload_fileobj(
                        buffer,
                        self._bucket,
                        thumb_key,
                        ExtraArgs={"ContentType": content_type},
                    )

            return True
        except ClientError as e:
            raise ImageStorageError(f"Failed to rotate S3 image: {e}")
        except Exception as e:
            raise ImageStorageError(f"Failed to rotate image: {e}")

    async def get_image(self, image_url: str) -> tuple[bytes, str]:
        """
        Get image content from storage.

        Args:
            image_url: URL/path to the image

        Returns:
            Tuple of (image_bytes, content_type)

        Raises:
            ImageStorageError: If image not found or retrieval fails
        """
        if self.storage_type == "local":
            return await self._get_local(image_url)
        else:
            return await self._get_s3(image_url)

    async def _get_local(self, image_url: str) -> tuple[bytes, str]:
        """Get image from local filesystem."""
        if not image_url.startswith("/uploads/"):
            raise ImageStorageError("Invalid image URL")

        image_path = self.base_path / image_url[9:]
        if not image_path.exists():
            raise ImageStorageError("Image not found")

        # Determine content type from extension
        ext = image_path.suffix.lower()
        content_type = (
            "image/jpeg"
            if ext in (".jpg", ".jpeg")
            else "image/png"
            if ext == ".png"
            else "image/webp"
            if ext == ".webp"
            else "application/octet-stream"
        )

        return image_path.read_bytes(), content_type

    async def _get_s3(self, image_url: str) -> tuple[bytes, str]:
        """Get image from S3/MinIO storage."""
        if not image_url.startswith("/uploads/"):
            raise ImageStorageError("Invalid image URL")

        try:
            image_key = image_url[9:]  # Remove /uploads/ prefix
            response = self._s3_client.get_object(Bucket=self._bucket, Key=image_key)
            content = response["Body"].read()
            content_type = response.get("ContentType", "application/octet-stream")
            return content, content_type
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ImageStorageError("Image not found")
            raise ImageStorageError(f"Failed to get image from S3: {e}")


# Singleton instance
_image_storage: Optional[ImageStorage] = None


def get_image_storage() -> ImageStorage:
    """Get image storage singleton."""
    global _image_storage
    if _image_storage is None:
        _image_storage = ImageStorage()
    return _image_storage
