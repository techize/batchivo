"""Pydantic schemas for inventory transactions."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.inventory_transaction import TransactionType


class InventoryTransactionBase(BaseModel):
    """Base schema for inventory transactions."""

    transaction_type: TransactionType
    weight_before: Decimal = Field(..., description="Spool weight before transaction (grams)")
    weight_change: Decimal = Field(..., description="Weight change (negative for usage)")
    weight_after: Decimal = Field(..., description="Spool weight after transaction (grams)")
    description: str = Field(..., max_length=500)
    notes: Optional[str] = None
    transaction_metadata: Optional[dict] = Field(None, alias="metadata")


class InventoryTransactionCreate(BaseModel):
    """Schema for creating an adjustment transaction."""

    spool_id: UUID
    new_weight: Decimal = Field(..., ge=0, description="New weight value")
    reason: str = Field(..., max_length=200, description="Reason for adjustment")
    notes: Optional[str] = None


class InventoryTransactionResponse(InventoryTransactionBase):
    """Response schema for inventory transactions."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    tenant_id: UUID
    spool_id: UUID
    production_run_id: Optional[UUID] = None
    production_run_material_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    transaction_at: datetime
    reversal_of_id: Optional[UUID] = None
    is_reversal: bool
    created_at: datetime
    updated_at: datetime

    # Spool info (when loaded)
    spool_name: Optional[str] = None


class InventoryTransactionListResponse(BaseModel):
    """Response schema for listing transactions."""

    transactions: list[InventoryTransactionResponse]
    total: int
    page: int
    page_size: int


class InventoryTransactionSummary(BaseModel):
    """Summary of transactions for a spool."""

    spool_id: str
    total_transactions: int
    by_type: dict
    total_used: float
    total_returned: float
    total_adjusted: float
