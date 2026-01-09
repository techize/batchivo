"""Pydantic schemas for Consumable Inventory API."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# ConsumableType Schemas
# =============================================================================


class ConsumableTypeBase(BaseModel):
    """Base consumable type schema with common fields."""

    sku: str = Field(..., min_length=1, max_length=50, description="Unique SKU within tenant")
    name: str = Field(..., min_length=1, max_length=200, description="Human-readable name")
    description: Optional[str] = Field(None, description="Detailed description")
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Category (magnets, inserts, hardware, finishing, packaging)",
    )

    # Unit information
    unit_of_measure: str = Field(
        "each",
        max_length=20,
        description="Unit of measure (each, ml, g, pack)",
    )

    # Current pricing
    current_cost_per_unit: Optional[float] = Field(None, ge=0, description="Current cost per unit")

    # Stock management
    quantity_on_hand: int = Field(0, ge=0, description="Current stock quantity")
    reorder_point: Optional[int] = Field(
        None, ge=0, description="Stock level that triggers reorder alert"
    )
    reorder_quantity: Optional[int] = Field(
        None, ge=0, description="Suggested quantity to order when reordering"
    )

    # Supplier information
    preferred_supplier: Optional[str] = Field(
        None, max_length=200, description="Preferred supplier/vendor name"
    )
    supplier_sku: Optional[str] = Field(
        None, max_length=100, description="Supplier's SKU/product code"
    )
    supplier_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL to purchase from supplier (e.g., Amazon product link)",
    )
    typical_lead_days: Optional[int] = Field(
        None, ge=0, description="Typical delivery time in days"
    )

    # Status
    is_active: bool = Field(True, description="Whether this consumable is active")


class ConsumableTypeCreate(ConsumableTypeBase):
    """Schema for creating a new consumable type."""

    pass  # Inherits all fields from ConsumableTypeBase


class ConsumableTypeUpdate(BaseModel):
    """Schema for updating a consumable type (all fields optional)."""

    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    unit_of_measure: Optional[str] = Field(None, max_length=20)
    current_cost_per_unit: Optional[float] = Field(None, ge=0)
    quantity_on_hand: Optional[int] = Field(None, ge=0)
    reorder_point: Optional[int] = Field(None, ge=0)
    reorder_quantity: Optional[int] = Field(None, ge=0)
    preferred_supplier: Optional[str] = Field(None, max_length=200)
    supplier_sku: Optional[str] = Field(None, max_length=100)
    supplier_url: Optional[str] = Field(None, max_length=500)
    typical_lead_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ConsumableTypeResponse(ConsumableTypeBase):
    """Schema for consumable type responses."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    # Computed fields
    is_low_stock: bool = Field(..., description="Whether stock is below reorder point")
    stock_value: float = Field(..., description="Total value of stock on hand")

    model_config = ConfigDict(from_attributes=True)


class ConsumableTypeListResponse(BaseModel):
    """Schema for paginated consumable type list."""

    total: int = Field(..., description="Total number of consumable types")
    consumables: list[ConsumableTypeResponse] = Field(..., description="List of consumable types")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


# =============================================================================
# ConsumablePurchase Schemas
# =============================================================================


class ConsumablePurchaseBase(BaseModel):
    """Base consumable purchase schema with common fields."""

    consumable_type_id: UUID = Field(..., description="Consumable type being purchased")
    quantity_purchased: int = Field(..., ge=1, description="Quantity purchased")
    total_cost: float = Field(..., ge=0, description="Total cost of purchase")

    # Source
    supplier: Optional[str] = Field(None, max_length=200, description="Supplier/vendor name")
    order_reference: Optional[str] = Field(
        None, max_length=100, description="Order number or reference"
    )
    purchase_url: Optional[str] = Field(
        None, max_length=500, description="URL to purchase (e.g., Amazon product link)"
    )
    purchase_date: Optional[date] = Field(None, description="Date of purchase")

    notes: Optional[str] = Field(None, description="Additional notes")


class ConsumablePurchaseCreate(ConsumablePurchaseBase):
    """Schema for creating a new consumable purchase."""

    pass  # Inherits all fields from ConsumablePurchaseBase


class ConsumablePurchaseUpdate(BaseModel):
    """Schema for updating a consumable purchase (all fields optional)."""

    quantity_purchased: Optional[int] = Field(None, ge=1)
    total_cost: Optional[float] = Field(None, ge=0)
    supplier: Optional[str] = Field(None, max_length=200)
    order_reference: Optional[str] = Field(None, max_length=100)
    purchase_url: Optional[str] = Field(None, max_length=500)
    purchase_date: Optional[date] = None
    notes: Optional[str] = None


class ConsumablePurchaseResponse(ConsumablePurchaseBase):
    """Schema for consumable purchase responses."""

    id: UUID
    tenant_id: UUID
    cost_per_unit: float = Field(..., description="Cost per unit")
    quantity_remaining: int = Field(..., description="Remaining quantity from this purchase")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsumablePurchaseWithType(ConsumablePurchaseResponse):
    """Schema for consumable purchase with nested type info."""

    consumable_sku: str = Field(..., description="Consumable SKU")
    consumable_name: str = Field(..., description="Consumable name")


class ConsumablePurchaseListResponse(BaseModel):
    """Schema for paginated consumable purchase list."""

    total: int = Field(..., description="Total number of purchases")
    purchases: list[ConsumablePurchaseWithType] = Field(..., description="List of purchases")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


# =============================================================================
# ConsumableUsage Schemas
# =============================================================================


class ConsumableUsageBase(BaseModel):
    """Base consumable usage schema with common fields."""

    consumable_type_id: UUID = Field(..., description="Consumable type used")
    quantity_used: int = Field(
        ..., description="Quantity used (positive) or adjusted (negative for returns)"
    )

    # Optional links
    production_run_id: Optional[UUID] = Field(
        None, description="Production run that used this consumable"
    )
    product_id: Optional[UUID] = Field(None, description="Product that used this consumable")

    # Context
    usage_type: str = Field(
        "production",
        max_length=50,
        description="Type of usage (production, adjustment, waste, return)",
    )
    notes: Optional[str] = Field(None, description="Usage notes or reason for adjustment")


class ConsumableUsageCreate(ConsumableUsageBase):
    """Schema for creating a new consumable usage record."""

    pass  # Inherits all fields from ConsumableUsageBase


class ConsumableUsageResponse(ConsumableUsageBase):
    """Schema for consumable usage responses."""

    id: UUID
    tenant_id: UUID
    cost_at_use: Optional[float] = Field(None, description="Cost per unit at time of use")
    total_cost: float = Field(..., description="Total cost of this usage")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsumableUsageWithDetails(ConsumableUsageResponse):
    """Schema for consumable usage with nested details."""

    consumable_sku: str = Field(..., description="Consumable SKU")
    consumable_name: str = Field(..., description="Consumable name")


class ConsumableUsageListResponse(BaseModel):
    """Schema for paginated consumable usage list."""

    total: int = Field(..., description="Total number of usage records")
    usage: list[ConsumableUsageWithDetails] = Field(..., description="List of usage records")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


# =============================================================================
# Stock Adjustment Schema
# =============================================================================


class StockAdjustment(BaseModel):
    """Schema for adjusting stock levels."""

    quantity_adjustment: int = Field(
        ..., description="Quantity to add (positive) or remove (negative)"
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Reason for adjustment",
    )
    notes: Optional[str] = Field(None, description="Additional notes")


# =============================================================================
# Low Stock Alert Schema
# =============================================================================


class LowStockAlert(BaseModel):
    """Schema for low stock alert."""

    consumable_id: UUID
    sku: str
    name: str
    quantity_on_hand: int
    reorder_point: int
    reorder_quantity: Optional[int]
    preferred_supplier: Optional[str]
    stock_value: float
