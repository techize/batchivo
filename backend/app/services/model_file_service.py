"""Model file service for managing 3D model files (STL, 3MF, gcode, etc.)."""

import logging
import os
import uuid
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.model import Model
from app.models.model_file import FileLocation, ModelFile, ModelFileType
from app.models.tenant import Tenant
from app.models.user import User
from app.services.image_storage import ImageStorageError, get_image_storage

logger = logging.getLogger(__name__)

# Allowed 3D file types
ALLOWED_CONTENT_TYPES = {
    # STL files
    "model/stl": ".stl",
    "application/sla": ".stl",
    "application/vnd.ms-pki.stl": ".stl",
    "application/octet-stream": None,  # May be STL or 3MF, check extension
    # 3MF files
    "model/3mf": ".3mf",
    "application/vnd.ms-package.3dmanufacturing-3dmodel+xml": ".3mf",
    "application/zip": ".3mf",  # 3MF is a ZIP file
    # Gcode
    "text/x-gcode": ".gcode",
    "text/plain": None,  # May be gcode, check extension
}

# File extensions we support
ALLOWED_EXTENSIONS = {".stl", ".3mf", ".gcode", ".gco", ".g"}

# File size limits
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB for large gcode files


class ModelFileStorageError(Exception):
    """Error during model file storage operation."""

    pass


def extract_3mf_thumbnail(file_content: bytes) -> Optional[Tuple[bytes, str]]:
    """
    Extract embedded thumbnail from a 3MF file.

    3MF files are ZIP archives that may contain a thumbnail image at:
    - Metadata/thumbnail.png (standard location)
    - Metadata/thumbnail.jpg
    - 3D/Metadata/thumbnail.png (some slicers)

    Args:
        file_content: Raw bytes of the 3MF file

    Returns:
        Tuple of (thumbnail_bytes, content_type) if found, None otherwise
    """
    # Standard 3MF thumbnail locations (in order of preference)
    thumbnail_paths = [
        "Metadata/thumbnail.png",
        "Metadata/thumbnail.jpg",
        "Metadata/thumbnail.jpeg",
        "3D/Metadata/thumbnail.png",
        "3D/Metadata/thumbnail.jpg",
        # BambuStudio/OrcaSlicer often use these
        "Metadata/plate_1.png",
        "Metadata/top.png",
    ]

    try:
        with zipfile.ZipFile(BytesIO(file_content), "r") as zf:
            # Get list of files in the archive (case-insensitive search)
            namelist = zf.namelist()
            namelist_lower = {n.lower(): n for n in namelist}

            for thumb_path in thumbnail_paths:
                # Try exact match first
                if thumb_path in namelist:
                    thumbnail_data = zf.read(thumb_path)
                    content_type = (
                        "image/png" if thumb_path.endswith(".png") else "image/jpeg"
                    )
                    logger.info(f"Extracted 3MF thumbnail from: {thumb_path}")
                    return (thumbnail_data, content_type)

                # Try case-insensitive match
                if thumb_path.lower() in namelist_lower:
                    actual_path = namelist_lower[thumb_path.lower()]
                    thumbnail_data = zf.read(actual_path)
                    content_type = (
                        "image/png" if actual_path.lower().endswith(".png") else "image/jpeg"
                    )
                    logger.info(f"Extracted 3MF thumbnail from: {actual_path}")
                    return (thumbnail_data, content_type)

            logger.debug(f"No thumbnail found in 3MF. Files: {namelist[:10]}...")
            return None

    except zipfile.BadZipFile:
        logger.warning("File is not a valid ZIP/3MF archive")
        return None
    except Exception as e:
        logger.warning(f"Failed to extract 3MF thumbnail: {e}")
        return None


class ModelFileService:
    """
    Service for managing 3D model files.

    Handles file upload, storage, retrieval, and deletion.
    Supports local filesystem and S3/MinIO storage backends.
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant: Tenant,
        user: Optional[User] = None,
    ):
        """
        Initialize the model file service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Current tenant for isolation
            user: Current user performing actions (optional, for audit trail)
        """
        self.db = db
        self.tenant = tenant
        self.user = user
        self.settings = get_settings()
        self.storage_type = self.settings.storage_type
        self.base_path = Path(self.settings.storage_path)

        # Ensure local storage directory exists
        if self.storage_type == "local":
            self.base_path.mkdir(parents=True, exist_ok=True)
            (self.base_path / "models").mkdir(exist_ok=True)

        # Initialize S3 client if using S3 storage
        self._s3_client = None
        if self.storage_type == "s3":
            self._init_s3_client()

    def _init_s3_client(self):
        """Initialize S3/MinIO client."""
        logger.info(
            f"Initializing S3 client: endpoint={self.settings.storage_s3_endpoint or 'AWS S3'}, "
            f"bucket={self.settings.storage_s3_bucket}, region={self.settings.storage_s3_region}"
        )

        # Validate required configuration
        if not self.settings.storage_s3_access_key:
            logger.warning("S3 access key not configured (STORAGE_S3_ACCESS_KEY)")
        if not self.settings.storage_s3_secret_key:
            logger.warning("S3 secret key not configured (STORAGE_S3_SECRET_KEY)")
        if not self.settings.storage_s3_bucket:
            logger.warning("S3 bucket not configured (STORAGE_S3_BUCKET)")

        s3_config = {}
        if self.settings.storage_s3_endpoint:
            s3_config["endpoint_url"] = self.settings.storage_s3_endpoint

        try:
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.settings.storage_s3_access_key,
                aws_secret_access_key=self.settings.storage_s3_secret_key,
                region_name=self.settings.storage_s3_region,
                **s3_config,
            )
            self._bucket = self.settings.storage_s3_bucket
            logger.info("S3 client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self._s3_client = None
            self._bucket = None

    def _validate_file(
        self,
        file_content: bytes,
        content_type: str,
        original_filename: str,
    ) -> str:
        """
        Validate file and determine actual extension.

        Args:
            file_content: Raw file bytes
            content_type: MIME type
            original_filename: Original filename

        Returns:
            Validated file extension

        Raises:
            ModelFileStorageError: If validation fails
        """
        # Check file size
        if len(file_content) > MAX_FILE_SIZE:
            raise ModelFileStorageError(
                f"File too large: {len(file_content)} bytes. Maximum: {MAX_FILE_SIZE} bytes"
            )

        # Get extension from filename
        extension = Path(original_filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise ModelFileStorageError(
                f"Invalid file type: {extension}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        return extension

    async def upload_file(
        self,
        model_id: UUID,
        file_content: bytes,
        content_type: str,
        original_filename: str,
        file_type: ModelFileType,
        part_name: Optional[str] = None,
        version: Optional[str] = None,
        is_primary: bool = False,
        notes: Optional[str] = None,
    ) -> ModelFile:
        """
        Upload a 3D model file.

        Args:
            model_id: UUID of the model to attach file to
            file_content: Raw file bytes
            content_type: MIME type
            original_filename: Original filename
            file_type: Type of file (source_stl, slicer_project, etc.)
            part_name: Optional part name for multi-part models
            version: Optional version string
            is_primary: Whether this is the primary file
            notes: Optional user notes

        Returns:
            Created ModelFile instance

        Raises:
            ModelFileStorageError: If upload fails
        """
        logger.debug(
            f"upload_file called: model_id={model_id}, filename={original_filename}, "
            f"file_type={file_type}, size={len(file_content)}, storage={self.storage_type}"
        )

        # Validate the model exists and belongs to this tenant
        model = await self._get_model(model_id)
        if not model:
            logger.warning(f"Model not found: {model_id} for tenant {self.tenant.id}")
            raise ModelFileStorageError(f"Model not found: {model_id}")

        # Validate file
        extension = self._validate_file(file_content, content_type, original_filename)

        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{extension}"
        model_dir = f"models/{model_id}"

        # Upload to storage
        if self.storage_type == "local":
            file_url = await self._save_local(file_content, model_dir, filename)
        else:
            file_url = await self._save_s3(file_content, model_dir, filename, content_type)

        # Extract and save thumbnail from 3MF files if model has no image
        if extension == ".3mf" and not model.image_url:
            await self._extract_and_save_3mf_thumbnail(model, file_content)

        # If setting as primary, unset other primary files of same type
        if is_primary:
            await self._unset_primary_files(model_id, file_type)

        # Create database record
        model_file = ModelFile(
            tenant_id=self.tenant.id,
            model_id=model_id,
            file_type=file_type.value,
            file_location=FileLocation.UPLOADED.value,
            file_url=file_url,
            local_path=None,
            original_filename=original_filename,
            file_size=len(file_content),
            content_type=content_type,
            part_name=part_name,
            version=version,
            is_primary=is_primary,
            notes=notes,
            uploaded_at=datetime.utcnow(),
            uploaded_by_user_id=self.user.id if self.user else None,
        )

        self.db.add(model_file)
        await self.db.commit()
        await self.db.refresh(model_file)

        logger.info(
            f"Uploaded file '{original_filename}' for model {model_id} "
            f"(file_id={model_file.id}, size={len(file_content)})"
        )
        return model_file

    async def create_local_reference(
        self,
        model_id: UUID,
        local_path: str,
        file_type: ModelFileType,
        part_name: Optional[str] = None,
        version: Optional[str] = None,
        is_primary: bool = False,
        notes: Optional[str] = None,
    ) -> ModelFile:
        """
        Create a local file reference (no upload, just store the path).

        Args:
            model_id: UUID of the model to attach file to
            local_path: Local filesystem path to the file
            file_type: Type of file (source_stl, slicer_project, etc.)
            part_name: Optional part name for multi-part models
            version: Optional version string
            is_primary: Whether this is the primary file
            notes: Optional user notes

        Returns:
            Created ModelFile instance with file_location='local_reference'

        Raises:
            ModelFileStorageError: If model not found
        """
        logger.debug(
            f"create_local_reference called: model_id={model_id}, path={local_path}, "
            f"file_type={file_type}"
        )

        # Validate the model exists and belongs to this tenant
        model = await self._get_model(model_id)
        if not model:
            logger.warning(f"Model not found: {model_id} for tenant {self.tenant.id}")
            raise ModelFileStorageError(f"Model not found: {model_id}")

        # Extract filename from path
        path_obj = Path(local_path)
        original_filename = path_obj.name

        # Get file info if path exists
        file_size = None
        if path_obj.exists() and path_obj.is_file():
            file_size = path_obj.stat().st_size

        # Determine content type from extension
        extension = path_obj.suffix.lower()
        content_type = self._get_content_type_from_extension(extension)

        # If setting as primary, unset other primary files of same type
        if is_primary:
            await self._unset_primary_files(model_id, file_type)

        # Create database record
        model_file = ModelFile(
            tenant_id=self.tenant.id,
            model_id=model_id,
            file_type=file_type.value,
            file_location=FileLocation.LOCAL_REFERENCE.value,
            file_url=None,
            local_path=local_path,
            original_filename=original_filename,
            file_size=file_size,
            content_type=content_type,
            part_name=part_name,
            version=version,
            is_primary=is_primary,
            notes=notes,
            uploaded_at=datetime.utcnow(),
            uploaded_by_user_id=self.user.id if self.user else None,
        )

        self.db.add(model_file)
        await self.db.commit()
        await self.db.refresh(model_file)

        logger.info(
            f"Created local reference for model {model_id}: '{local_path}' "
            f"(file_id={model_file.id})"
        )
        return model_file

    def _get_content_type_from_extension(self, extension: str) -> Optional[str]:
        """Get MIME content type from file extension."""
        content_types = {
            ".stl": "model/stl",
            ".3mf": "model/3mf",
            ".gcode": "text/x-gcode",
            ".gco": "text/x-gcode",
            ".g": "text/x-gcode",
        }
        return content_types.get(extension)

    @staticmethod
    def validate_local_path(path: str) -> dict:
        """
        Validate a local filesystem path.

        Args:
            path: Local filesystem path to validate

        Returns:
            dict with: exists, is_file, file_size, filename
        """
        path_obj = Path(path)
        exists = path_obj.exists()
        is_file = path_obj.is_file() if exists else False
        file_size = path_obj.stat().st_size if is_file else None
        filename = path_obj.name if path_obj.name else None

        return {
            "path": path,
            "exists": exists,
            "is_file": is_file,
            "file_size": file_size,
            "filename": filename,
        }

    def check_local_path_exists(self, local_path: str) -> bool:
        """Check if a local file path exists and is a file."""
        path_obj = Path(local_path)
        return path_obj.exists() and path_obj.is_file()

    async def _save_local(
        self,
        file_content: bytes,
        model_dir: str,
        filename: str,
    ) -> str:
        """Save file to local filesystem."""
        full_dir = self.base_path / model_dir
        full_dir.mkdir(parents=True, exist_ok=True)

        file_path = full_dir / filename
        file_path.write_bytes(file_content)

        return f"/uploads/{model_dir}/{filename}"

    async def _save_s3(
        self,
        file_content: bytes,
        model_dir: str,
        filename: str,
        content_type: str,
    ) -> str:
        """Save file to S3/MinIO storage."""
        # Verify S3 client is initialized
        if self._s3_client is None:
            logger.error("S3 client not initialized but storage_type is 's3'")
            raise ModelFileStorageError(
                "S3 storage not configured. Please check STORAGE_S3_* environment variables."
            )

        if not self._bucket:
            logger.error("S3 bucket name not configured")
            raise ModelFileStorageError("S3 bucket not configured. Please set STORAGE_S3_BUCKET.")

        try:
            file_key = f"{model_dir}/{filename}"
            logger.debug(f"Uploading to S3: bucket={self._bucket}, key={file_key}")

            self._s3_client.upload_fileobj(
                BytesIO(file_content),
                self._bucket,
                file_key,
                ExtraArgs={"ContentType": content_type},
            )

            logger.info(f"Successfully uploaded to S3: {file_key}")
            return f"/uploads/{file_key}"

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"S3 upload failed: {error_code} - {error_msg}")

            # Provide helpful error messages for common issues
            if error_code == "NoSuchBucket":
                raise ModelFileStorageError(
                    f"S3 bucket '{self._bucket}' does not exist. "
                    "Please create it or check the STORAGE_S3_BUCKET configuration."
                )
            elif error_code == "AccessDenied":
                raise ModelFileStorageError(
                    f"Access denied to S3 bucket '{self._bucket}'. "
                    "Please check your S3 credentials and bucket permissions."
                )
            elif error_code == "InvalidAccessKeyId":
                raise ModelFileStorageError(
                    "Invalid S3 access key. Please check STORAGE_S3_ACCESS_KEY."
                )
            elif error_code == "SignatureDoesNotMatch":
                raise ModelFileStorageError(
                    "Invalid S3 secret key. Please check STORAGE_S3_SECRET_KEY."
                )
            else:
                raise ModelFileStorageError(f"S3 upload failed: {error_code} - {error_msg}")

        except Exception as e:
            logger.exception(f"Unexpected error during S3 upload: {e}")
            raise ModelFileStorageError(f"Unexpected error during file upload: {e}")

    async def _get_model(self, model_id: UUID) -> Optional[Model]:
        """Get model by ID within tenant."""
        result = await self.db.execute(
            select(Model).where(Model.id == model_id).where(Model.tenant_id == self.tenant.id)
        )
        return result.scalar_one_or_none()

    async def _unset_primary_files(self, model_id: UUID, file_type: ModelFileType):
        """Unset is_primary for all files of the same type for this model."""
        result = await self.db.execute(
            select(ModelFile)
            .where(ModelFile.model_id == model_id)
            .where(ModelFile.tenant_id == self.tenant.id)
            .where(ModelFile.file_type == file_type.value)
            .where(ModelFile.is_primary == True)  # noqa: E712
        )
        for file in result.scalars().all():
            file.is_primary = False

    async def _extract_and_save_3mf_thumbnail(
        self,
        model: Model,
        file_content: bytes,
    ) -> bool:
        """
        Extract thumbnail from 3MF file and save as model preview image.

        Args:
            model: The Model instance to update
            file_content: Raw bytes of the 3MF file

        Returns:
            True if thumbnail was extracted and saved, False otherwise
        """
        # Extract thumbnail from 3MF
        thumbnail_result = extract_3mf_thumbnail(file_content)
        if not thumbnail_result:
            logger.debug(f"No thumbnail found in 3MF for model {model.id}")
            return False

        thumbnail_data, content_type = thumbnail_result

        try:
            # Use ImageStorage to save the thumbnail
            image_storage = get_image_storage()
            result = await image_storage.save_image(
                file_content=thumbnail_data,
                content_type=content_type,
                product_id=str(model.id),  # Use model ID for the image path
                original_filename=f"3mf_thumbnail.{'png' if 'png' in content_type else 'jpg'}",
            )

            # Update model with the new image URL
            model.image_url = result["image_url"]
            logger.info(
                f"Saved 3MF thumbnail for model {model.id}: {result['image_url']}"
            )
            return True

        except ImageStorageError as e:
            logger.warning(f"Failed to save 3MF thumbnail for model {model.id}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error saving 3MF thumbnail: {e}")
            return False

    async def get_file(self, file_id: UUID) -> Optional[ModelFile]:
        """
        Get a model file by ID.

        Args:
            file_id: UUID of the file

        Returns:
            ModelFile instance or None if not found
        """
        result = await self.db.execute(
            select(ModelFile)
            .where(ModelFile.id == file_id)
            .where(ModelFile.tenant_id == self.tenant.id)
        )
        return result.scalar_one_or_none()

    async def list_files_for_model(
        self,
        model_id: UUID,
        file_type: Optional[ModelFileType] = None,
    ) -> List[ModelFile]:
        """
        List all files for a model.

        Args:
            model_id: UUID of the model
            file_type: Optional filter by file type

        Returns:
            List of ModelFile instances
        """
        query = (
            select(ModelFile)
            .where(ModelFile.model_id == model_id)
            .where(ModelFile.tenant_id == self.tenant.id)
        )

        if file_type:
            query = query.where(ModelFile.file_type == file_type.value)

        query = query.order_by(ModelFile.is_primary.desc(), ModelFile.uploaded_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_primary_file(
        self,
        model_id: UUID,
        file_type: Optional[ModelFileType] = None,
    ) -> Optional[ModelFile]:
        """
        Get the primary file for a model.

        Args:
            model_id: UUID of the model
            file_type: Optional filter by file type

        Returns:
            Primary ModelFile or None if not found
        """
        query = (
            select(ModelFile)
            .where(ModelFile.model_id == model_id)
            .where(ModelFile.tenant_id == self.tenant.id)
            .where(ModelFile.is_primary == True)  # noqa: E712
        )

        if file_type:
            query = query.where(ModelFile.file_type == file_type.value)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_file_metadata(
        self,
        file_id: UUID,
        part_name: Optional[str] = None,
        version: Optional[str] = None,
        is_primary: Optional[bool] = None,
        notes: Optional[str] = None,
    ) -> Optional[ModelFile]:
        """
        Update file metadata.

        Args:
            file_id: UUID of the file
            part_name: New part name (if provided)
            version: New version (if provided)
            is_primary: New primary status (if provided)
            notes: New notes (if provided)

        Returns:
            Updated ModelFile or None if not found
        """
        model_file = await self.get_file(file_id)
        if not model_file:
            return None

        if part_name is not None:
            model_file.part_name = part_name
        if version is not None:
            model_file.version = version
        if notes is not None:
            model_file.notes = notes
        if is_primary is not None:
            if is_primary:
                # Unset other primary files of same type
                await self._unset_primary_files(
                    model_file.model_id,
                    ModelFileType(model_file.file_type),
                )
            model_file.is_primary = is_primary

        await self.db.commit()
        await self.db.refresh(model_file)

        logger.info(f"Updated file metadata for {file_id}")
        return model_file

    async def delete_file(self, file_id: UUID) -> bool:
        """
        Delete a model file.

        Args:
            file_id: UUID of the file

        Returns:
            True if deleted, False if not found
        """
        model_file = await self.get_file(file_id)
        if not model_file:
            return False

        # Delete from storage (only for uploaded files, not local references)
        if model_file.file_location != FileLocation.LOCAL_REFERENCE.value:
            if self.storage_type == "local":
                await self._delete_local(model_file.file_url)
            else:
                await self._delete_s3(model_file.file_url)
        # Note: Local references just remove the DB record, not the actual file

        # Delete database record
        await self.db.delete(model_file)
        await self.db.commit()

        logger.info(f"Deleted file {file_id} ({model_file.original_filename})")
        return True

    async def _delete_local(self, file_url: str) -> bool:
        """Delete file from local filesystem."""
        try:
            if file_url.startswith("/uploads/"):
                file_path = self.base_path / file_url[9:]
                if file_path.exists():
                    file_path.unlink()
            return True
        except Exception as e:
            logger.warning(f"Failed to delete local file: {e}")
            return False

    async def _delete_s3(self, file_url: str) -> bool:
        """Delete file from S3/MinIO storage."""
        try:
            if file_url.startswith("/uploads/"):
                file_key = file_url[9:]
                self._s3_client.delete_object(Bucket=self._bucket, Key=file_key)
            return True
        except ClientError as e:
            logger.warning(f"Failed to delete S3 file: {e}")
            return False

    async def get_file_content(self, file_id: UUID) -> tuple[bytes, str, str]:
        """
        Get file content for download.

        Args:
            file_id: UUID of the file

        Returns:
            Tuple of (file_bytes, content_type, original_filename)

        Raises:
            ModelFileStorageError: If file not found or retrieval fails
        """
        model_file = await self.get_file(file_id)
        if not model_file:
            raise ModelFileStorageError("File not found")

        # Handle local reference files
        if model_file.file_location == FileLocation.LOCAL_REFERENCE.value:
            if not model_file.local_path:
                raise ModelFileStorageError("Local path not set for local reference file")
            content = await self._get_local_reference(model_file.local_path)
        elif self.storage_type == "local":
            content = await self._get_local(model_file.file_url)
        else:
            content = await self._get_s3(model_file.file_url)

        return (
            content,
            model_file.content_type or "application/octet-stream",
            model_file.original_filename,
        )

    async def _get_local_reference(self, local_path: str) -> bytes:
        """Get file from local filesystem reference path."""
        path_obj = Path(local_path)
        if not path_obj.exists():
            raise ModelFileStorageError(f"Local file not found: {local_path}")
        if not path_obj.is_file():
            raise ModelFileStorageError(f"Path is not a file: {local_path}")
        return path_obj.read_bytes()

    async def _get_local(self, file_url: str) -> bytes:
        """Get file from local filesystem."""
        if not file_url.startswith("/uploads/"):
            raise ModelFileStorageError("Invalid file URL")

        file_path = self.base_path / file_url[9:]
        if not file_path.exists():
            raise ModelFileStorageError("File not found on disk")

        return file_path.read_bytes()

    async def _get_s3(self, file_url: str) -> bytes:
        """Get file from S3/MinIO storage."""
        if not file_url.startswith("/uploads/"):
            raise ModelFileStorageError("Invalid file URL")

        try:
            file_key = file_url[9:]
            response = self._s3_client.get_object(Bucket=self._bucket, Key=file_key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise ModelFileStorageError("File not found in S3")
            raise ModelFileStorageError(f"Failed to get file from S3: {e}")
