"""Pydantic schemas for Product API (sellable items composed of models)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.product_variant import FulfilmentType


# Product Model (join table) schemas
class ProductModelBase(BaseModel):
    """Base schema for product-model relationship."""

    model_id: UUID = Field(..., description="Model ID")
    quantity: int = Field(1, gt=0, description="Quantity of this model in the product")


class ProductModelCreate(ProductModelBase):
    """Schema for adding a model to a product."""

    pass


class ProductModelResponse(ProductModelBase):
    """Schema for product-model in response."""

    id: UUID
    product_id: UUID
    model_name: Optional[str] = Field(None, description="Model name (from join)")
    model_sku: Optional[str] = Field(None, description="Model SKU (from join)")
    model_cost: Optional[Decimal] = Field(None, description="Model cost per unit")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Product Component (join table for Product -> Product) schemas
class ProductComponentBase(BaseModel):
    """Base schema for product-component relationship (product containing another product)."""

    child_product_id: UUID = Field(..., description="Child product ID")
    quantity: int = Field(1, gt=0, description="Quantity of this child product in the parent")


class ProductComponentCreate(ProductComponentBase):
    """Schema for adding a child product to a parent product (creating a bundle)."""

    pass


class ProductComponentUpdate(BaseModel):
    """Schema for updating a product component (quantity only)."""

    quantity: int = Field(..., gt=0, description="Quantity of this child product in the parent")


class ProductComponentResponse(ProductComponentBase):
    """Schema for product-component in response."""

    id: UUID
    parent_product_id: UUID
    child_product_name: Optional[str] = Field(None, description="Child product name")
    child_product_sku: Optional[str] = Field(None, description="Child product SKU")
    child_product_cost: Optional[Decimal] = Field(None, description="Child product total make cost")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Product Pricing schemas
class ProductPricingBase(BaseModel):
    """Base schema for product pricing."""

    sales_channel_id: UUID = Field(..., description="Sales channel ID")
    list_price: Decimal = Field(..., ge=0, description="List price on this channel")
    is_active: bool = Field(True, description="Whether this pricing is active")


class ProductPricingCreate(ProductPricingBase):
    """Schema for creating product pricing."""

    pass


class ProductPricingUpdate(BaseModel):
    """Schema for updating product pricing."""

    list_price: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductPricingResponse(ProductPricingBase):
    """Schema for product pricing in response."""

    id: UUID
    product_id: UUID
    channel_name: Optional[str] = Field(None, description="Sales channel name")
    platform_type: Optional[str] = Field(None, description="Platform type")
    platform_fee: Optional[Decimal] = Field(None, description="Calculated platform fee")
    net_revenue: Optional[Decimal] = Field(None, description="Net revenue after fees")
    profit: Optional[Decimal] = Field(None, description="Profit after make cost")
    margin_percentage: Optional[Decimal] = Field(None, description="Profit margin %")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Cost breakdown schema
class ProductCostBreakdown(BaseModel):
    """Product cost breakdown."""

    models_cost: Decimal = Field(..., description="Total cost of all models")
    child_products_cost: Decimal = Field(
        Decimal("0"), description="Total cost of child products (for bundles)"
    )
    packaging_cost: Decimal = Field(..., description="Packaging cost")
    assembly_cost: Decimal = Field(..., description="Assembly labor cost")
    total_make_cost: Decimal = Field(..., description="Total make cost")
    # Phase 3: Actual cost tracking from production runs
    models_actual_cost: Optional[Decimal] = Field(
        None, description="Total actual production cost of models (from rolling averages)"
    )
    total_actual_cost: Optional[Decimal] = Field(
        None, description="Total actual make cost (if all models have production data)"
    )
    cost_variance_percentage: Optional[Decimal] = Field(
        None, description="Variance between theoretical and actual costs (%)"
    )
    models_with_actual_cost: int = Field(
        0, description="Number of models with actual production cost data"
    )
    models_total: int = Field(0, description="Total number of distinct models in product")

    model_config = ConfigDict(from_attributes=True)


# Product schemas
class ProductBase(BaseModel):
    """Base product schema with common fields."""

    sku: str = Field(..., min_length=1, max_length=100, description="Stock Keeping Unit")
    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    designer_id: Optional[UUID] = Field(None, description="Designer who created this product")
    units_in_stock: int = Field(0, ge=0, description="Number of packaged units in inventory")
    packaging_cost: Decimal = Field(
        Decimal("0"), ge=0, description="Manual packaging cost (used if no consumable linked)"
    )
    packaging_consumable_id: Optional[UUID] = Field(
        None, description="Consumable used for packaging (e.g., box)"
    )
    packaging_quantity: int = Field(
        1, ge=1, description="Quantity of packaging consumable per product"
    )
    assembly_minutes: int = Field(0, ge=0, description="Assembly time in minutes")
    is_active: bool = Field(True, description="Whether product is active")
    shop_visible: bool = Field(False, description="Whether product is visible in the public shop")
    print_to_order: bool = Field(
        False, description="Whether product is printed to order (vs in-stock)"
    )
    free_shipping: bool = Field(False, description="Whether product qualifies for free shipping")
    # Shop display fields
    shop_description: Optional[str] = Field(None, description="Rich HTML description for shop")
    is_featured: bool = Field(False, description="Whether product is featured in showcase")
    is_dragon: bool = Field(False, description="Whether product appears in the Dragons collection")
    feature_title: Optional[str] = Field(
        None, max_length=100, description="Custom title for featured display"
    )
    backstory: Optional[str] = Field(None, description="Backstory/lore for featured items")
    # Product specifications
    weight_grams: Optional[int] = Field(None, ge=0, description="Product weight in grams")
    size_cm: Optional[Decimal] = Field(None, ge=0, description="Product size/length in centimeters")
    print_time_hours: Optional[Decimal] = Field(None, ge=0, description="Print time in hours")
    # Multi-channel publishing fields
    tags: list[str] = Field(default_factory=list, description="Keyword tags for Shopify/Etsy discoverability")
    product_type: Optional[str] = Field(None, max_length=100, description="Product type (e.g. '3D Print') for Shopify")
    seo_slug: Optional[str] = Field(None, max_length=200, description="URL-friendly handle (auto-generated from name if null)")
    seo_title: Optional[str] = Field(None, max_length=200, description="SEO meta title (≤60 chars)")
    seo_description: Optional[str] = Field(None, max_length=300, description="SEO meta description (≤155 chars)")
    material: Optional[str] = Field(None, max_length=100, description="Primary material (e.g. 'PLA')")
    colour_options: list[str] = Field(default_factory=list, description="Available filament colour options")
    etsy_taxonomy_id: Optional[int] = Field(None, description="Etsy taxonomy integer ID")


class ProductCreate(ProductBase):
    """Schema for creating a new product."""

    models: Optional[list[ProductModelCreate]] = Field(
        default_factory=list, description="Models to include in this product"
    )
    child_products: Optional[list[ProductComponentCreate]] = Field(
        default_factory=list, description="Other products to include in this bundle"
    )


class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)."""

    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    designer_id: Optional[UUID] = None
    units_in_stock: Optional[int] = Field(None, ge=0)
    packaging_cost: Optional[Decimal] = Field(None, ge=0)
    packaging_consumable_id: Optional[UUID] = None
    packaging_quantity: Optional[int] = Field(None, ge=1)
    assembly_minutes: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    shop_visible: Optional[bool] = None
    print_to_order: Optional[bool] = None
    free_shipping: Optional[bool] = None
    # Shop display fields
    shop_description: Optional[str] = None
    is_featured: Optional[bool] = None
    is_dragon: Optional[bool] = None
    feature_title: Optional[str] = Field(None, max_length=100)
    backstory: Optional[str] = None
    # Product specifications
    weight_grams: Optional[int] = Field(None, ge=0)
    size_cm: Optional[Decimal] = Field(None, ge=0)
    print_time_hours: Optional[Decimal] = Field(None, ge=0)
    # Multi-channel publishing fields
    tags: Optional[list[str]] = None
    product_type: Optional[str] = Field(None, max_length=100)
    seo_slug: Optional[str] = Field(None, max_length=200)
    seo_title: Optional[str] = Field(None, max_length=200)
    seo_description: Optional[str] = Field(None, max_length=300)
    material: Optional[str] = Field(None, max_length=100)
    colour_options: Optional[list[str]] = None
    etsy_taxonomy_id: Optional[int] = None


class ProductResponse(ProductBase):
    """Schema for product responses (without details)."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    # Computed fields for list views
    total_make_cost: Optional[Decimal] = Field(None, description="Total make cost (all components)")
    suggested_price: Optional[Decimal] = Field(
        None, description="Suggested retail price (2.5x markup)"
    )
    # Designer info (populated from join)
    designer_name: Optional[str] = Field(None, description="Designer name")
    designer_slug: Optional[str] = Field(None, description="Designer slug for URLs")
    designer_logo_url: Optional[str] = Field(None, description="Designer logo URL")

    model_config = ConfigDict(from_attributes=True)


# Brief category info for product responses
class ProductCategoryBrief(BaseModel):
    """Brief category info for product responses."""

    id: UUID
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


# Brief external listing info for product responses
class ExternalListingBrief(BaseModel):
    """Brief external listing info for product responses."""

    id: UUID
    platform: str
    external_id: str
    external_url: Optional[str] = None
    sync_status: str
    last_synced_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductDetailResponse(ProductResponse):
    """Schema for detailed product response (with models, child products, pricing, and cost)."""

    models: list[ProductModelResponse] = Field(
        default_factory=list, description="Models in this product"
    )
    child_products: list[ProductComponentResponse] = Field(
        default_factory=list, description="Child products in this bundle"
    )
    pricing: list[ProductPricingResponse] = Field(
        default_factory=list, description="Channel pricing"
    )
    cost_breakdown: ProductCostBreakdown = Field(..., description="Cost breakdown")
    # Packaging consumable info (if linked)
    packaging_consumable_name: Optional[str] = Field(None, description="Packaging consumable name")
    packaging_consumable_sku: Optional[str] = Field(None, description="Packaging consumable SKU")
    packaging_consumable_cost: Optional[Decimal] = Field(
        None, description="Cost per unit of packaging consumable"
    )
    # Categories this product belongs to
    categories: list[ProductCategoryBrief] = Field(
        default_factory=list, description="Categories this product belongs to"
    )
    # External marketplace listings
    external_listings: list[ExternalListingBrief] = Field(
        default_factory=list, description="External marketplace listings (Etsy, eBay, etc.)"
    )
    # Size variants
    variants: list["ProductVariantResponse"] = Field(
        default_factory=list, description="Size variants with per-size pricing and stock info"
    )

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    """Schema for paginated product list."""

    products: list[ProductResponse]
    total: int
    skip: int
    limit: int

    model_config = ConfigDict(from_attributes=True)


# ── Product Variant schemas ────────────────────────────────────────────────────


class ProductVariantBase(BaseModel):
    """Fields shared by create and update."""

    size: str = Field(..., min_length=1, max_length=50, description="Size label (e.g. Small, M, XL)")
    display_order: int = Field(0, ge=0, description="Sort order (lower = first)")
    sku: Optional[str] = Field(None, max_length=120, description="Variant SKU (auto-generated if omitted)")
    price_adjustment_pence: int = Field(0, description="Price adjustment from base price in pence")
    units_in_stock: int = Field(0, ge=0, description="Units held in stock")
    fulfilment_type: FulfilmentType = Field(FulfilmentType.STOCK, description="stock or print_to_order")
    lead_time_days: Optional[int] = Field(None, ge=1, description="Days to dispatch (print-to-order only)")
    material_cost_pence: Optional[int] = Field(None, ge=0, description="Filament cost for this size in pence")
    print_time_hours: Optional[Decimal] = Field(None, ge=0, description="Estimated print time in hours")
    is_active: bool = Field(True, description="Whether this variant is available for sale")


class ProductVariantCreate(ProductVariantBase):
    """Schema for creating a product variant."""

    pass


class ProductVariantUpdate(BaseModel):
    """Schema for updating a product variant (all fields optional)."""

    size: Optional[str] = Field(None, min_length=1, max_length=50)
    display_order: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, max_length=120)
    price_adjustment_pence: Optional[int] = None
    units_in_stock: Optional[int] = Field(None, ge=0)
    fulfilment_type: Optional[FulfilmentType] = None
    lead_time_days: Optional[int] = Field(None, ge=1)
    material_cost_pence: Optional[int] = Field(None, ge=0)
    print_time_hours: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductVariantResponse(BaseModel):
    """Schema for returning a product variant."""

    id: UUID
    product_id: UUID
    size: str
    display_order: int
    sku: str
    price_adjustment_pence: int
    units_in_stock: int
    fulfilment_type: FulfilmentType
    lead_time_days: Optional[int]
    material_cost_pence: Optional[int]
    print_time_hours: Optional[Decimal]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
