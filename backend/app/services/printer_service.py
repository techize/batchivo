"""Printer service for managing 3D printers."""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.printer import Printer
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.printer import (
    PrinterCreate,
    PrinterUpdate,
    PrinterResponse,
    PrinterListResponse,
)

logger = logging.getLogger(__name__)


class PrinterService:
    """Service for managing printers."""

    def __init__(self, db: AsyncSession, tenant: Tenant, user: Optional[User] = None):
        """
        Initialize the printer service.

        Args:
            db: AsyncSession instance for database operations
            tenant: Current tenant for isolation
            user: Current user performing actions (optional, for audit trail)
        """
        self.db = db
        self.tenant = tenant
        self.user = user

    async def create_printer(self, data: PrinterCreate) -> Printer:
        """
        Create a new printer.

        Args:
            data: PrinterCreate schema with printer data

        Returns:
            Created Printer instance
        """
        printer = Printer(
            tenant_id=self.tenant.id,
            **data.model_dump(),
        )

        self.db.add(printer)
        await self.db.commit()
        await self.db.refresh(printer)

        logger.info(
            f"Created printer '{printer.name}' (id={printer.id}) for tenant {self.tenant.id}"
        )
        return printer

    async def get_printer(self, printer_id: UUID) -> Optional[Printer]:
        """
        Get a printer by ID.

        Args:
            printer_id: UUID of the printer

        Returns:
            Printer instance or None if not found
        """
        result = await self.db.execute(
            select(Printer)
            .where(Printer.id == printer_id)
            .where(Printer.tenant_id == self.tenant.id)
        )
        return result.scalar_one_or_none()

    async def get_printer_by_name(self, name: str) -> Optional[Printer]:
        """
        Get a printer by name within the tenant.

        Args:
            name: Printer name

        Returns:
            Printer instance or None if not found
        """
        result = await self.db.execute(
            select(Printer).where(Printer.name == name).where(Printer.tenant_id == self.tenant.id)
        )
        return result.scalar_one_or_none()

    async def list_printers(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> PrinterListResponse:
        """
        List printers with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Optional filter by active status

        Returns:
            PrinterListResponse with printers and pagination info
        """
        # Build query
        query = select(Printer).where(Printer.tenant_id == self.tenant.id)

        if is_active is not None:
            query = query.where(Printer.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Printer.name).offset(skip).limit(limit)
        result = await self.db.execute(query)
        printers = list(result.scalars().all())

        return PrinterListResponse(
            printers=[PrinterResponse.model_validate(p) for p in printers],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def update_printer(
        self,
        printer_id: UUID,
        data: PrinterUpdate,
    ) -> Optional[Printer]:
        """
        Update a printer.

        Args:
            printer_id: UUID of the printer to update
            data: PrinterUpdate schema with fields to update

        Returns:
            Updated Printer instance or None if not found
        """
        printer = await self.get_printer(printer_id)
        if not printer:
            return None

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(printer, field, value)

        await self.db.commit()
        await self.db.refresh(printer)

        logger.info(f"Updated printer '{printer.name}' (id={printer.id})")
        return printer

    async def delete_printer(self, printer_id: UUID) -> bool:
        """
        Delete a printer (soft delete by setting is_active=False).

        Args:
            printer_id: UUID of the printer to delete

        Returns:
            True if deleted, False if not found
        """
        printer = await self.get_printer(printer_id)
        if not printer:
            return False

        printer.is_active = False
        await self.db.commit()

        logger.info(f"Soft-deleted printer '{printer.name}' (id={printer.id})")
        return True

    async def hard_delete_printer(self, printer_id: UUID) -> bool:
        """
        Permanently delete a printer.

        Args:
            printer_id: UUID of the printer to delete

        Returns:
            True if deleted, False if not found
        """
        printer = await self.get_printer(printer_id)
        if not printer:
            return False

        await self.db.delete(printer)
        await self.db.commit()

        logger.info(f"Hard-deleted printer '{printer.name}' (id={printer_id})")
        return True

    async def get_active_printers(self) -> List[Printer]:
        """
        Get all active printers for the tenant.

        Returns:
            List of active Printer instances
        """
        result = await self.db.execute(
            select(Printer)
            .where(Printer.tenant_id == self.tenant.id)
            .where(Printer.is_active.is_(True))  # noqa: E712
            .order_by(Printer.name)
        )
        return list(result.scalars().all())
