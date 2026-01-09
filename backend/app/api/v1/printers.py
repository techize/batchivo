"""Printer management API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.schemas.printer import (
    PrinterCreate,
    PrinterListResponse,
    PrinterResponse,
    PrinterUpdate,
)
from app.services.printer_service import PrinterService

router = APIRouter()


@router.post("", response_model=PrinterResponse, status_code=status.HTTP_201_CREATED)
async def create_printer(
    printer_data: PrinterCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> PrinterResponse:
    """
    Create a new printer.

    Requires authentication.
    Printer will be associated with current tenant.
    """
    service = PrinterService(db, tenant, user)
    printer = await service.create_printer(printer_data)
    return PrinterResponse.model_validate(printer)


@router.get("", response_model=PrinterListResponse)
async def list_printers(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max items to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> PrinterListResponse:
    """
    List all printers for current tenant with pagination.

    Supports:
    - Pagination (skip, limit)
    - Filter by active status
    """
    service = PrinterService(db, tenant, user)
    return await service.list_printers(skip=skip, limit=limit, is_active=is_active)


@router.get("/{printer_id}", response_model=PrinterResponse)
async def get_printer(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> PrinterResponse:
    """
    Get printer details by ID.

    Requires authentication.
    Printer must belong to current tenant.
    """
    service = PrinterService(db, tenant, user)
    printer = await service.get_printer(printer_id)

    if not printer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Printer not found",
        )

    return PrinterResponse.model_validate(printer)


@router.put("/{printer_id}", response_model=PrinterResponse)
async def update_printer(
    printer_id: UUID,
    printer_data: PrinterUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> PrinterResponse:
    """
    Update an existing printer.

    Requires authentication.
    Printer must belong to current tenant.
    """
    service = PrinterService(db, tenant, user)
    printer = await service.update_printer(printer_id, printer_data)

    if not printer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Printer not found",
        )

    return PrinterResponse.model_validate(printer)


@router.delete("/{printer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_printer(
    printer_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a printer (soft delete by setting is_active=False).

    Requires authentication.
    Printer must belong to current tenant.
    """
    service = PrinterService(db, tenant, user)
    result = await service.delete_printer(printer_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Printer not found",
        )
