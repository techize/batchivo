"""Pydantic schemas for Shop API (public storefront endpoints)."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Product Image Schemas
# =============================================================================


class ShopProductImageResponse(BaseModel):
    """Product image for shop display."""

    id: UUID
    url: str = Field(..., description="Full image URL")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    alt: str = Field("", description="Alt text for accessibility")
    is_primary: bool = Field(False, description="Whether this is the main product image")
    order: int = Field(0, description="Display order (lower = first)")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Product Schemas
# =============================================================================


class ShopProductSummary(BaseModel):
    """Product summary for listing pages (minimal data for performance)."""

    id: UUID
    sku: str
    name: str
    price: Decimal = Field(..., description="Shop price in pounds")
    primary_image_url: Optional[str] = Field(None, description="Primary product image URL")
    primary_image_thumbnail: Optional[str] = Field(None, description="Primary image thumbnail")
    is_sold: bool = Field(False, description="Whether product is sold (stock = 0)")
    is_featured: bool = Field(False, description="Whether product is featured")
    free_shipping: bool = Field(False, description="Whether product qualifies for free shipping")
    category_slugs: list[str] = Field(default_factory=list, description="Category slugs")

    model_config = ConfigDict(from_attributes=True)


class ShopProductDetail(ShopProductSummary):
    """Full product detail for product pages."""

    # Descriptions (shop_description preferred, falls back to description)
    shop_description: Optional[str] = Field(None, description="Rich HTML shop description")
    description: Optional[str] = Field(None, description="Fallback description")

    # All images
    images: list[ShopProductImageResponse] = Field(
        default_factory=list, description="All product images"
    )

    # Featured/showcase fields
    feature_title: Optional[str] = Field(
        None, description="Custom title for featured display (e.g., dragon name)"
    )
    backstory: Optional[str] = Field(None, description="Backstory/lore for featured items")

    # Categories with full info
    categories: list["ShopCategorySummary"] = Field(
        default_factory=list, description="Product categories"
    )

    # Related products
    related_products: list[ShopProductSummary] = Field(
        default_factory=list, description="Related/similar products"
    )

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Category Schemas
# =============================================================================


class ShopCategorySummary(BaseModel):
    """Category summary for navigation."""

    id: UUID
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class ShopCategoryResponse(BaseModel):
    """Full category for category listing and pages."""

    id: UUID
    name: str
    slug: str
    description: Optional[str] = Field(None, description="Category description")
    image_url: Optional[str] = Field(None, description="Hero/banner image URL")
    product_count: int = Field(0, description="Number of visible products in category")
    display_order: int = Field(0, description="Display order (lower = first)")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# List Response Schemas
# =============================================================================


class ShopProductListResponse(BaseModel):
    """Paginated product list response."""

    data: list[ShopProductSummary]
    total: int = Field(..., description="Total matching products")
    page: int = Field(1, description="Current page (1-indexed)")
    limit: int = Field(24, description="Items per page")
    has_more: bool = Field(False, description="Whether more pages exist")

    model_config = ConfigDict(from_attributes=True)


class ShopCategoryListResponse(BaseModel):
    """Category list response."""

    data: list[ShopCategoryResponse]
    total: int = Field(..., description="Total categories")

    model_config = ConfigDict(from_attributes=True)


class ShopDragonListResponse(BaseModel):
    """Dragon showcase response (featured products with backstories)."""

    data: list[ShopProductDetail]
    total: int = Field(..., description="Total dragons")

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Query Parameter Schemas
# =============================================================================


class ShopProductFilters(BaseModel):
    """Query parameters for product listing."""

    category: Optional[str] = Field(None, description="Filter by category slug")
    sort: str = Field("newest", description="Sort order: newest, price_asc, price_desc, name")
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(24, ge=1, le=100, description="Items per page")
    include_sold: bool = Field(True, description="Include sold items in results")

    model_config = ConfigDict(from_attributes=True)


# Update forward references
ShopProductDetail.model_rebuild()
