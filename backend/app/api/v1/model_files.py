"""Model files API endpoints for 3D file management (STL, 3MF, gcode, etc.)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.model_file import ModelFileType
from app.schemas.model_file import (
    ModelFileListResponse,
    ModelFileResponse,
    ModelFileUpdate,
    ModelFileUploadResponse,
    ModelFileType as SchemaFileType,
)
from app.services.model_file_service import ModelFileService, ModelFileStorageError

router = APIRouter()


def get_file_service(
    db: AsyncSession,
    tenant,
    user,
) -> ModelFileService:
    """Create ModelFileService instance."""
    return ModelFileService(db=db, tenant=tenant, user=user)


@router.post(
    "/{model_id}/files",
    response_model=ModelFileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a model file",
    description="Upload a 3D model file (STL, 3MF, gcode) for a model.",
)
async def upload_file(
    model_id: UUID,
    file: UploadFile = File(..., description="The file to upload"),
    file_type: SchemaFileType = Form(..., description="Type of file"),
    part_name: Optional[str] = Form(None, description="Part name for multi-part models"),
    version: Optional[str] = Form(None, description="Version identifier"),
    is_primary: bool = Form(False, description="Set as primary file"),
    notes: Optional[str] = Form(None, description="Notes about the file"),
    user: CurrentUser = None,
    tenant: CurrentTenant = None,
    db: AsyncSession = Depends(get_db),
) -> ModelFileUploadResponse:
    """
    Upload a 3D model file.

    Supports STL, 3MF, and gcode files up to 500MB.
    File type must be specified (source_stl, source_3mf, slicer_project, gcode, plate_layout).
    """
    service = get_file_service(db, tenant, user)

    try:
        # Read file content
        content = await file.read()

        # Upload file
        model_file = await service.upload_file(
            model_id=model_id,
            file_content=content,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "unnamed",
            file_type=ModelFileType(file_type.value),
            part_name=part_name,
            version=version,
            is_primary=is_primary,
            notes=notes,
        )

        return ModelFileUploadResponse(
            file=ModelFileResponse.model_validate(model_file),
            message=f"File '{file.filename}' uploaded successfully",
        )

    except ModelFileStorageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{model_id}/files",
    response_model=ModelFileListResponse,
    summary="List model files",
    description="Get all files associated with a model.",
)
async def list_files(
    model_id: UUID,
    file_type: Optional[SchemaFileType] = Query(None, description="Filter by file type"),
    user: CurrentUser = None,
    tenant: CurrentTenant = None,
    db: AsyncSession = Depends(get_db),
) -> ModelFileListResponse:
    """
    List all files for a model.

    Optionally filter by file type.
    Results are sorted with primary files first, then by upload date.
    """
    service = get_file_service(db, tenant, user)

    files = await service.list_files_for_model(
        model_id=model_id,
        file_type=ModelFileType(file_type.value) if file_type else None,
    )

    return ModelFileListResponse(
        files=[ModelFileResponse.model_validate(f) for f in files],
        total=len(files),
    )


@router.get(
    "/{model_id}/files/{file_id}",
    response_model=ModelFileResponse,
    summary="Get file details",
    description="Get details about a specific model file.",
)
async def get_file(
    model_id: UUID,
    file_id: UUID,
    user: CurrentUser = None,
    tenant: CurrentTenant = None,
    db: AsyncSession = Depends(get_db),
) -> ModelFileResponse:
    """Get details about a specific file."""
    service = get_file_service(db, tenant, user)

    model_file = await service.get_file(file_id)

    if not model_file or model_file.model_id != model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return ModelFileResponse.model_validate(model_file)


@router.get(
    "/{model_id}/files/{file_id}/download",
    summary="Download file",
    description="Download the actual file content.",
    responses={
        200: {
            "description": "File content",
            "content": {"application/octet-stream": {}},
        }
    },
)
async def download_file(
    model_id: UUID,
    file_id: UUID,
    user: CurrentUser = None,
    tenant: CurrentTenant = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Download a model file.

    Returns the file content with appropriate headers for download.
    """
    service = get_file_service(db, tenant, user)

    # Verify file exists and belongs to this model
    model_file = await service.get_file(file_id)
    if not model_file or model_file.model_id != model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    try:
        content, content_type, filename = await service.get_file_content(file_id)

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(content)),
            },
        )

    except ModelFileStorageError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch(
    "/{model_id}/files/{file_id}",
    response_model=ModelFileResponse,
    summary="Update file metadata",
    description="Update metadata for a model file.",
)
async def update_file(
    model_id: UUID,
    file_id: UUID,
    update_data: ModelFileUpdate,
    user: CurrentUser = None,
    tenant: CurrentTenant = None,
    db: AsyncSession = Depends(get_db),
) -> ModelFileResponse:
    """
    Update file metadata.

    Can update part_name, version, is_primary, and notes.
    Setting is_primary=true will unset other primary files of the same type.
    """
    service = get_file_service(db, tenant, user)

    # Verify file exists and belongs to this model
    existing = await service.get_file(file_id)
    if not existing or existing.model_id != model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    model_file = await service.update_file_metadata(
        file_id=file_id,
        part_name=update_data.part_name,
        version=update_data.version,
        is_primary=update_data.is_primary,
        notes=update_data.notes,
    )

    return ModelFileResponse.model_validate(model_file)


@router.delete(
    "/{model_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete file",
    description="Delete a model file.",
)
async def delete_file(
    model_id: UUID,
    file_id: UUID,
    user: CurrentUser = None,
    tenant: CurrentTenant = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a model file.

    Removes the file from storage and database.
    This action cannot be undone.
    """
    service = get_file_service(db, tenant, user)

    # Verify file exists and belongs to this model
    existing = await service.get_file(file_id)
    if not existing or existing.model_id != model_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    deleted = await service.delete_file(file_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        )


@router.get(
    "/{model_id}/files/primary",
    response_model=ModelFileResponse,
    summary="Get primary file",
    description="Get the primary file for a model, optionally filtered by type.",
)
async def get_primary_file(
    model_id: UUID,
    file_type: Optional[SchemaFileType] = Query(None, description="Filter by file type"),
    user: CurrentUser = None,
    tenant: CurrentTenant = None,
    db: AsyncSession = Depends(get_db),
) -> ModelFileResponse:
    """
    Get the primary file for a model.

    Returns the file marked as is_primary=true.
    Optionally filter by file type.
    """
    service = get_file_service(db, tenant, user)

    model_file = await service.get_primary_file(
        model_id=model_id,
        file_type=ModelFileType(file_type.value) if file_type else None,
    )

    if not model_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No primary file found",
        )

    return ModelFileResponse.model_validate(model_file)
