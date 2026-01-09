"""Pydantic schemas for Model API (printed items)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Cost breakdown schema
class CostBreakdown(BaseModel):
    """Model cost breakdown."""

    material_cost: Decimal = Field(..., description="Total material cost from BOM")
    component_cost: Decimal = Field(..., description="Total component cost")
    labor_cost: Decimal = Field(..., description="Labor cost (hours × rate)")
    overhead_cost: Decimal = Field(..., description="Overhead cost")
    total_cost: Decimal = Field(..., description="Total model cost")

    model_config = ConfigDict(from_attributes=True)


# Model Material (BOM) schemas
class ModelMaterialBase(BaseModel):
    """Base schema for model materials (BOM entry)."""

    spool_id: UUID = Field(..., description="Spool ID (material type + color + brand)")
    weight_grams: Decimal = Field(..., gt=0, description="Weight of material used in grams")
    cost_per_gram: Decimal = Field(..., ge=0, description="Cost per gram (snapshot)")


class ModelMaterialCreate(ModelMaterialBase):
    """Schema for adding material to model."""

    pass


class ModelMaterialResponse(ModelMaterialBase):
    """Schema for material in model response."""

    id: UUID
    model_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Model Component schemas
class ModelComponentBase(BaseModel):
    """Base schema for model components."""

    component_name: str = Field(..., min_length=1, max_length=200, description="Component name")
    quantity: int = Field(..., gt=0, description="Quantity of this component")
    unit_cost: Decimal = Field(..., ge=0, description="Cost per unit")
    supplier: Optional[str] = Field(None, max_length=200, description="Supplier name")


class ModelComponentCreate(ModelComponentBase):
    """Schema for adding component to model."""

    pass


class ModelComponentResponse(ModelComponentBase):
    """Schema for component in model response."""

    id: UUID
    model_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Model schemas
class ModelBase(BaseModel):
    """Base model schema with common fields."""

    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit")
    name: str = Field(..., min_length=1, max_length=200, description="Model name")
    description: Optional[str] = Field(None, description="Model description")
    category: Optional[str] = Field(None, max_length=100, description="Model category")
    image_url: Optional[str] = Field(None, max_length=500, description="Model image URL")
    labor_hours: Decimal = Field(Decimal("0"), ge=0, description="Labor hours required")
    labor_rate_override: Optional[Decimal] = Field(
        None, ge=0, description="Override labor rate (£/hour)"
    )
    overhead_percentage: Decimal = Field(
        Decimal("0"), ge=0, le=100, description="Overhead percentage (0-100)"
    )
    is_active: bool = Field(True, description="Whether model is active")
    # Metadata fields
    designer: Optional[str] = Field(None, max_length=200, description="Model designer name")
    source: Optional[str] = Field(None, max_length=200, description="Model source platform")
    print_time_minutes: Optional[int] = Field(
        None, ge=0, description="Print time in minutes (for full plate)"
    )
    prints_per_plate: int = Field(
        1,
        ge=1,
        description="Number of items per plate (material weight and print time are divided by this)",
    )
    machine: Optional[str] = Field(None, max_length=100, description="Printer/machine used")
    last_printed_date: Optional[datetime] = Field(
        None, description="Last time this model was printed"
    )
    units_in_stock: Optional[int] = Field(
        0, ge=0, description="Number of printed units in inventory"
    )


class ModelCreate(ModelBase):
    """Schema for creating a new model."""

    pass


class ModelUpdate(BaseModel):
    """Schema for updating a model (all fields optional)."""

    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)
    labor_hours: Optional[Decimal] = Field(None, ge=0)
    labor_rate_override: Optional[Decimal] = Field(None, ge=0)
    overhead_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    # Metadata fields
    designer: Optional[str] = Field(None, max_length=200)
    source: Optional[str] = Field(None, max_length=200)
    print_time_minutes: Optional[int] = Field(None, ge=0)
    prints_per_plate: Optional[int] = Field(None, ge=1)
    machine: Optional[str] = Field(None, max_length=100)
    last_printed_date: Optional[datetime] = None
    units_in_stock: Optional[int] = Field(None, ge=0)


class ModelResponse(ModelBase):
    """Schema for model responses (without BOM/components)."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    # Computed cost (included when materials/components are loaded)
    total_cost: Optional[Decimal] = Field(None, description="Total build cost (computed)")

    model_config = ConfigDict(from_attributes=True)


class ModelDetailResponse(ModelResponse):
    """Schema for detailed model response (with BOM, components, and cost)."""

    materials: list[ModelMaterialResponse] = Field(
        default_factory=list, description="Bill of Materials"
    )
    components: list[ModelComponentResponse] = Field(
        default_factory=list, description="Model components"
    )
    cost_breakdown: CostBreakdown = Field(..., description="Cost breakdown")

    model_config = ConfigDict(from_attributes=True)


# Production Defaults schemas (for auto-populating production runs)
class BOMSpoolSuggestion(BaseModel):
    """Spool suggestion from model BOM with current inventory info."""

    spool_id: UUID = Field(..., description="Spool ID")
    spool_name: str = Field(..., description="Spool name (Brand - Material - Color)")
    material_type_code: str = Field(..., description="Material type code (e.g., PLA, PETG)")
    color: str = Field(..., description="Spool color name")
    color_hex: Optional[str] = Field(None, description="Hex color code")
    weight_grams: Decimal = Field(..., description="Weight from model BOM (grams)")
    cost_per_gram: Decimal = Field(..., description="Cost per gram snapshot")
    current_weight: Decimal = Field(..., description="Current spool weight available (grams)")
    is_active: bool = Field(..., description="Whether spool is active")

    model_config = ConfigDict(from_attributes=True)


class ModelProductionDefaults(BaseModel):
    """Production defaults for a model (BOM, printer, print time)."""

    model_id: UUID = Field(..., description="Model ID")
    sku: str = Field(..., description="Model SKU")
    name: str = Field(..., description="Model name")
    machine: Optional[str] = Field(None, description="Suggested printer/machine")
    print_time_minutes: Optional[int] = Field(
        None, description="Print time for full plate (minutes)"
    )
    prints_per_plate: int = Field(..., description="Number of items per plate")
    bom_materials: list[BOMSpoolSuggestion] = Field(
        default_factory=list, description="Bill of Materials with current inventory"
    )

    model_config = ConfigDict(from_attributes=True)


class ModelListResponse(BaseModel):
    """Schema for paginated model list."""

    models: list[ModelResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)
