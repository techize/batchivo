"""Product catalog API endpoints (sellable items composed of models)."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentTenant, CurrentUser, RequireAdmin
from app.database import get_db
from app.models.designer import Designer
from app.models.model import Model
from app.models.product import Product
from app.models.product_component import ProductComponent
from app.models.product_image import ProductImage
from app.models.product_model import ProductModel
from app.models.product_pricing import ProductPricing
from app.models.sales_channel import SalesChannel
from app.schemas.product import (
    ProductComponentCreate,
    ProductComponentResponse,
    ProductComponentUpdate,
    ProductCreate,
    ProductDetailResponse,
    ProductListResponse,
    ProductModelCreate,
    ProductModelResponse,
    ProductPricingCreate,
    ProductPricingResponse,
    ProductPricingUpdate,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.product_image import (
    ProductImageResponse,
    ProductImageUpdate,
    ProductImageListResponse,
)
from app.services.costing import CostingService
from app.services.etsy_sync import EtsySyncService, EtsySyncError
from app.services.image_storage import ImageStorage, ImageStorageError, get_image_storage
from app.services.search_service import SearchService, get_search_service
from app.schemas.external_listing import SyncToEtsyRequest, SyncToEtsyResponse, ExternalListingResponse

router = APIRouter()


def _get_product_load_options():
    """
    Get SQLAlchemy selectinload options for loading a Product with all
    relationships needed for cost calculation.

    This includes nested loading for child products to support recursive
    cost calculation without lazy loading (which fails in async context).
    """
    return [
        # Load product models with their model details
        selectinload(Product.product_models)
        .selectinload(ProductModel.model)
        .selectinload(Model.materials),
        selectinload(Product.product_models)
        .selectinload(ProductModel.model)
        .selectinload(Model.components),
        # Load child products with THEIR relationships (for recursive cost calc)
        # Level 1: child products
        selectinload(Product.child_products)
        .selectinload(ProductComponent.child_product)
        .selectinload(Product.product_models)
        .selectinload(ProductModel.model)
        .selectinload(Model.materials),
        selectinload(Product.child_products)
        .selectinload(ProductComponent.child_product)
        .selectinload(Product.product_models)
        .selectinload(ProductModel.model)
        .selectinload(Model.components),
        selectinload(Product.child_products)
        .selectinload(ProductComponent.child_product)
        .selectinload(Product.packaging_consumable),
        # Level 2: grandchild products (child's child products)
        selectinload(Product.child_products)
        .selectinload(ProductComponent.child_product)
        .selectinload(Product.child_products)
        .selectinload(ProductComponent.child_product)
        .selectinload(Product.product_models)
        .selectinload(ProductModel.model),
        selectinload(Product.child_products)
        .selectinload(ProductComponent.child_product)
        .selectinload(Product.child_products)
        .selectinload(ProductComponent.child_product)
        .selectinload(Product.packaging_consumable),
        # Load pricing with sales channels
        selectinload(Product.pricing).selectinload(ProductPricing.sales_channel),
        # Load packaging consumable
        selectinload(Product.packaging_consumable),
        # Load designer for attribution
        selectinload(Product.designer),
        # Load categories
        selectinload(Product.categories),
    ]


# Helper function to calculate and attach cost breakdown
async def product_with_cost(product: Product, db: AsyncSession) -> dict:
    """Convert Product model to response dict with cost breakdown."""
    cost_breakdown = CostingService.calculate_product_cost(product)

    # Build model responses with details
    model_responses = []
    for pm in product.product_models:
        model_cost = CostingService.calculate_model_cost(pm.model) if pm.model else None
        model_responses.append(
            {
                "id": pm.id,
                "product_id": pm.product_id,
                "model_id": pm.model_id,
                "quantity": pm.quantity,
                "model_name": pm.model.name if pm.model else None,
                "model_sku": pm.model.sku if pm.model else None,
                "model_cost": model_cost.total_cost if model_cost else None,
                "created_at": pm.created_at,
            }
        )

    # Build child product responses with details (for bundles)
    child_product_responses = []
    for pc in getattr(product, "child_products", []):
        child = pc.child_product
        if child:
            child_cost = CostingService.calculate_product_cost(child)
            child_product_responses.append(
                {
                    "id": pc.id,
                    "parent_product_id": pc.parent_product_id,
                    "child_product_id": pc.child_product_id,
                    "quantity": pc.quantity,
                    "child_product_name": child.name,
                    "child_product_sku": child.sku,
                    "child_product_cost": child_cost.total_make_cost,
                    "created_at": pc.created_at,
                }
            )

    # Build pricing responses with profit calculations
    pricing_responses = []
    for pricing in product.pricing:
        channel = pricing.sales_channel
        profit_data = CostingService.calculate_profit(
            list_price=Decimal(str(pricing.list_price)),
            make_cost=cost_breakdown.total_make_cost,
            fee_percentage=Decimal(str(channel.fee_percentage)) if channel else Decimal("0"),
            fee_fixed=Decimal(str(channel.fee_fixed)) if channel else Decimal("0"),
        )
        pricing_responses.append(
            {
                "id": pricing.id,
                "product_id": pricing.product_id,
                "sales_channel_id": pricing.sales_channel_id,
                "list_price": pricing.list_price,
                "is_active": pricing.is_active,
                "channel_name": channel.name if channel else None,
                "platform_type": channel.platform_type if channel else None,
                "platform_fee": profit_data["platform_fee"],
                "net_revenue": profit_data["net_revenue"],
                "profit": profit_data["profit"],
                "margin_percentage": profit_data["margin_percentage"],
                "created_at": pricing.created_at,
                "updated_at": pricing.updated_at,
            }
        )

    # Get packaging consumable info if linked
    packaging_consumable = getattr(product, "packaging_consumable", None)

    # Get designer info if linked
    designer = getattr(product, "designer", None)

    # Get categories
    categories = getattr(product, "categories", [])
    category_responses = [{"id": cat.id, "name": cat.name, "slug": cat.slug} for cat in categories]

    return {
        **{k: v for k, v in product.__dict__.items() if not k.startswith("_")},
        "models": model_responses,
        "child_products": child_product_responses,
        "pricing": pricing_responses,
        "cost_breakdown": cost_breakdown,
        "packaging_consumable_name": packaging_consumable.name if packaging_consumable else None,
        "packaging_consumable_sku": packaging_consumable.sku if packaging_consumable else None,
        "packaging_consumable_cost": packaging_consumable.current_cost_per_unit
        if packaging_consumable
        else None,
        # Designer info for attribution
        "designer_name": designer.name if designer else None,
        "designer_slug": designer.slug if designer else None,
        "designer_logo_url": designer.logo_url if designer else None,
        # Categories
        "categories": category_responses,
    }


@router.post("", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    _: RequireAdmin,
    db: AsyncSession = Depends(get_db),
) -> ProductDetailResponse:
    """
    Create a new product (sellable item).

    Requires admin role or higher.
    Product will be associated with current tenant.
    SKU must be unique per tenant.
    Can optionally include models (product_models) and child products (bundles) in creation.
    """
    # Check if SKU already exists for this tenant
    existing = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant.id,
            Product.sku == product_data.sku,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{product_data.sku}' already exists",
        )

    # Validate designer if provided
    if product_data.designer_id:
        designer = await db.get(Designer, product_data.designer_id)
        if not designer or designer.tenant_id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Designer {product_data.designer_id} not found",
            )

    # Extract models and child products for separate processing
    models_data = product_data.models or []
    child_products_data = product_data.child_products or []
    product_dict = product_data.model_dump(exclude={"models", "child_products"})

    # Create product instance
    product = Product(
        tenant_id=tenant.id,
        **product_dict,
    )

    db.add(product)
    await db.flush()  # Get the product ID

    # Add models if provided
    for model_data in models_data:
        # Verify model exists and belongs to tenant
        model = await db.get(Model, model_data.model_id)
        if not model or model.tenant_id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_data.model_id} not found",
            )

        product_model = ProductModel(
            product_id=product.id,
            model_id=model_data.model_id,
            quantity=model_data.quantity,
        )
        db.add(product_model)

    # Add child products if provided (for bundles)
    for child_data in child_products_data:
        # Verify child product exists and belongs to tenant
        child_product = await db.get(Product, child_data.child_product_id)
        if not child_product or child_product.tenant_id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Child product {child_data.child_product_id} not found",
            )

        # Prevent self-reference
        if child_data.child_product_id == product.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A product cannot contain itself",
            )

        product_component = ProductComponent(
            parent_product_id=product.id,
            child_product_id=child_data.child_product_id,
            quantity=child_data.quantity,
        )
        db.add(product_component)

    await db.commit()

    # Reload with relationships
    query = select(Product).where(Product.id == product.id).options(*_get_product_load_options())
    result = await db.execute(query)
    product = result.scalar_one()

    return ProductDetailResponse(**await product_with_cost(product, db))


@router.get("", response_model=ProductListResponse)
async def list_products(
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max items to return"),
    search: Optional[str] = Query(
        None, description="Full-text search by name, SKU, or description"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    designer_id: Optional[UUID] = Query(None, description="Filter by designer"),
    search_service: SearchService = Depends(get_search_service),
) -> ProductListResponse:
    """
    List all products for current tenant with pagination and filtering.

    Includes calculated make cost and suggested price for each product.
    Uses PostgreSQL full-text search when search parameter is provided.
    """
    # If search is provided, use the search service for FTS
    if search:
        # Use full-text search service
        products, total = await search_service.search_products(
            query=search,
            tenant_id=tenant.id,
            active_only=is_active if is_active is not None else True,
            limit=limit,
            offset=skip,
        )

        # Apply designer filter if provided (post-filter since FTS doesn't support it)
        if designer_id:
            products = [p for p in products if p.designer_id == designer_id]
            # Note: total might be inaccurate with post-filtering, but acceptable for search

        # Load relationships for cost calculation
        product_ids = [p.id for p in products]
        if product_ids:
            query = (
                select(Product)
                .where(Product.id.in_(product_ids))
                .options(*_get_product_load_options())
            )
            result = await db.execute(query)
            products_with_rels = {p.id: p for p in result.scalars().all()}
            products = [
                products_with_rels.get(p.id, p) for p in products if p.id in products_with_rels
            ]

        # Build response with calculated costs
        product_responses = []
        for product in products:
            cost_breakdown = CostingService.calculate_product_cost(product)
            total_make_cost = cost_breakdown.total_make_cost
            suggested_price = total_make_cost * Decimal("2.5")

            designer = getattr(product, "designer", None)

            product_dict = {
                "id": product.id,
                "tenant_id": product.tenant_id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "designer_id": product.designer_id,
                "packaging_cost": product.packaging_cost,
                "packaging_consumable_id": product.packaging_consumable_id,
                "packaging_quantity": product.packaging_quantity,
                "assembly_minutes": product.assembly_minutes,
                "units_in_stock": product.units_in_stock,
                "is_active": product.is_active,
                "shop_visible": product.shop_visible,
                "created_at": product.created_at,
                "updated_at": product.updated_at,
                "total_make_cost": total_make_cost,
                "suggested_price": suggested_price.quantize(Decimal("0.01")),
                "designer_name": designer.name if designer else None,
                "designer_slug": designer.slug if designer else None,
                "designer_logo_url": designer.logo_url if designer else None,
            }
            product_responses.append(ProductResponse(**product_dict))

        return ProductListResponse(
            products=product_responses,
            total=total,
            skip=skip,
            limit=limit,
        )

    # Standard query without FTS
    # Build base query
    base_query = select(Product).where(Product.tenant_id == tenant.id)

    if is_active is not None:
        base_query = base_query.where(Product.is_active == is_active)

    if designer_id is not None:
        base_query = base_query.where(Product.designer_id == designer_id)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination and fetch with relationships for cost calculation
    query = (
        base_query.options(*_get_product_load_options())
        .order_by(Product.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    # Build response with calculated costs
    product_responses = []
    for product in products:
        # Calculate cost breakdown
        cost_breakdown = CostingService.calculate_product_cost(product)
        total_make_cost = cost_breakdown.total_make_cost
        suggested_price = total_make_cost * Decimal("2.5")  # 2.5x markup

        # Get designer info
        designer = getattr(product, "designer", None)

        # Build response dict
        product_dict = {
            "id": product.id,
            "tenant_id": product.tenant_id,
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "designer_id": product.designer_id,
            "packaging_cost": product.packaging_cost,
            "packaging_consumable_id": product.packaging_consumable_id,
            "packaging_quantity": product.packaging_quantity,
            "assembly_minutes": product.assembly_minutes,
            "units_in_stock": product.units_in_stock,
            "is_active": product.is_active,
            "shop_visible": product.shop_visible,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "total_make_cost": total_make_cost,
            "suggested_price": suggested_price.quantize(Decimal("0.01")),
            # Designer info
            "designer_name": designer.name if designer else None,
            "designer_slug": designer.slug if designer else None,
            "designer_logo_url": designer.logo_url if designer else None,
        }
        product_responses.append(ProductResponse(**product_dict))

    return ProductListResponse(
        products=product_responses,
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductDetailResponse:
    """
    Get product detail with models, child products (bundles), pricing, and cost breakdown.
    """
    query = (
        select(Product)
        .where(
            Product.id == product_id,
            Product.tenant_id == tenant.id,
            Product.is_active.is_(True),
        )
        .options(*_get_product_load_options())
    )

    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ProductDetailResponse(**await product_with_cost(product, db))


@router.put("/{product_id}", response_model=ProductDetailResponse)
async def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductDetailResponse:
    """
    Update an existing product.
    """
    # Fetch product
    query = (
        select(Product)
        .where(
            Product.id == product_id,
            Product.tenant_id == tenant.id,
        )
        .options(*_get_product_load_options())
    )

    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check SKU uniqueness if changing
    if product_data.sku and product_data.sku != product.sku:
        existing = await db.execute(
            select(Product).where(
                Product.tenant_id == tenant.id,
                Product.sku == product_data.sku,
                Product.id != product_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product_data.sku}' already exists",
            )

    # Validate designer if being updated
    if product_data.designer_id is not None:
        designer = await db.get(Designer, product_data.designer_id)
        if not designer or designer.tenant_id != tenant.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Designer {product_data.designer_id} not found",
            )

    # Update fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return ProductDetailResponse(**await product_with_cost(product, db))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    _: RequireAdmin,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a product (soft delete by setting is_active=False).

    Requires admin role or higher.
    """
    query = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant.id,
    )

    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    product.is_active = False
    await db.commit()


# ==================== Product Models (Composition) Management ====================


@router.post(
    "/{product_id}/models", response_model=ProductModelResponse, status_code=status.HTTP_201_CREATED
)
async def add_product_model(
    product_id: UUID,
    model_data: ProductModelCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductModelResponse:
    """
    Add a model to product composition.
    """
    # Verify product exists and belongs to tenant
    product = await db.get(Product, product_id)
    if not product or product.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Verify model exists and belongs to tenant
    model = await db.get(Model, model_data.model_id)
    if not model or model.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if this model is already in the product
    existing = await db.execute(
        select(ProductModel).where(
            ProductModel.product_id == product_id,
            ProductModel.model_id == model_data.model_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This model is already in the product",
        )

    # Create product-model entry
    product_model = ProductModel(
        product_id=product_id,
        model_id=model_data.model_id,
        quantity=model_data.quantity,
    )

    db.add(product_model)
    await db.commit()
    await db.refresh(product_model)

    # Calculate model cost
    model_cost = CostingService.calculate_model_cost(model)

    return ProductModelResponse(
        id=product_model.id,
        product_id=product_model.product_id,
        model_id=product_model.model_id,
        quantity=product_model.quantity,
        model_name=model.name,
        model_sku=model.sku,
        model_cost=model_cost.total_cost,
        created_at=product_model.created_at,
    )


@router.put("/{product_id}/models/{product_model_id}", response_model=ProductModelResponse)
async def update_product_model(
    product_id: UUID,
    product_model_id: UUID,
    model_data: ProductModelCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductModelResponse:
    """
    Update a model's quantity in product composition.
    """
    # Fetch product-model with related model
    query = (
        select(ProductModel)
        .join(Product)
        .where(
            ProductModel.id == product_model_id,
            ProductModel.product_id == product_id,
            Product.tenant_id == tenant.id,
        )
        .options(selectinload(ProductModel.model))
    )

    result = await db.execute(query)
    product_model = result.scalar_one_or_none()

    if not product_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product model not found",
        )

    product_model.quantity = model_data.quantity
    await db.commit()
    await db.refresh(product_model)

    model_cost = CostingService.calculate_model_cost(product_model.model)

    return ProductModelResponse(
        id=product_model.id,
        product_id=product_model.product_id,
        model_id=product_model.model_id,
        quantity=product_model.quantity,
        model_name=product_model.model.name,
        model_sku=product_model.model.sku,
        model_cost=model_cost.total_cost,
        created_at=product_model.created_at,
    )


@router.delete("/{product_id}/models/{product_model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_product_model(
    product_id: UUID,
    product_model_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a model from product composition.
    """
    query = (
        select(ProductModel)
        .join(Product)
        .where(
            ProductModel.id == product_model_id,
            ProductModel.product_id == product_id,
            Product.tenant_id == tenant.id,
        )
    )

    result = await db.execute(query)
    product_model = result.scalar_one_or_none()

    if not product_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product model not found",
        )

    await db.delete(product_model)
    await db.commit()


# ==================== Product Pricing Management ====================


@router.post(
    "/{product_id}/pricing",
    response_model=ProductPricingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_product_pricing(
    product_id: UUID,
    pricing_data: ProductPricingCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductPricingResponse:
    """
    Add pricing for a product on a sales channel.
    """
    # Fetch product with models for cost calculation
    query = (
        select(Product)
        .where(
            Product.id == product_id,
            Product.tenant_id == tenant.id,
        )
        .options(
            selectinload(Product.product_models)
            .selectinload(ProductModel.model)
            .selectinload(Model.materials),
            selectinload(Product.product_models)
            .selectinload(ProductModel.model)
            .selectinload(Model.components),
        )
    )

    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Verify sales channel exists and belongs to tenant
    channel = await db.get(SalesChannel, pricing_data.sales_channel_id)
    if not channel or channel.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sales channel not found",
        )

    # Check if pricing already exists for this channel
    existing = await db.execute(
        select(ProductPricing).where(
            ProductPricing.product_id == product_id,
            ProductPricing.sales_channel_id == pricing_data.sales_channel_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pricing already exists for this sales channel",
        )

    # Create pricing entry
    pricing = ProductPricing(
        product_id=product_id,
        sales_channel_id=pricing_data.sales_channel_id,
        list_price=pricing_data.list_price,
        is_active=pricing_data.is_active,
    )

    db.add(pricing)
    await db.commit()
    await db.refresh(pricing)

    # Calculate profit
    cost_breakdown = CostingService.calculate_product_cost(product)
    profit_data = CostingService.calculate_profit(
        list_price=Decimal(str(pricing.list_price)),
        make_cost=cost_breakdown.total_make_cost,
        fee_percentage=Decimal(str(channel.fee_percentage)),
        fee_fixed=Decimal(str(channel.fee_fixed)),
    )

    return ProductPricingResponse(
        id=pricing.id,
        product_id=pricing.product_id,
        sales_channel_id=pricing.sales_channel_id,
        list_price=pricing.list_price,
        is_active=pricing.is_active,
        channel_name=channel.name,
        platform_type=channel.platform_type,
        platform_fee=profit_data["platform_fee"],
        net_revenue=profit_data["net_revenue"],
        profit=profit_data["profit"],
        margin_percentage=profit_data["margin_percentage"],
        created_at=pricing.created_at,
        updated_at=pricing.updated_at,
    )


@router.put("/{product_id}/pricing/{pricing_id}", response_model=ProductPricingResponse)
async def update_product_pricing(
    product_id: UUID,
    pricing_id: UUID,
    pricing_data: ProductPricingUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductPricingResponse:
    """
    Update product pricing.
    """
    # Fetch pricing with related data
    query = (
        select(ProductPricing)
        .join(Product)
        .where(
            ProductPricing.id == pricing_id,
            ProductPricing.product_id == product_id,
            Product.tenant_id == tenant.id,
        )
        .options(
            selectinload(ProductPricing.sales_channel),
            selectinload(ProductPricing.product)
            .selectinload(Product.product_models)
            .selectinload(ProductModel.model),
        )
    )

    result = await db.execute(query)
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found",
        )

    # Update fields
    update_data = pricing_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pricing, field, value)

    await db.commit()
    await db.refresh(pricing)

    # Calculate profit
    cost_breakdown = CostingService.calculate_product_cost(pricing.product)
    channel = pricing.sales_channel
    profit_data = CostingService.calculate_profit(
        list_price=Decimal(str(pricing.list_price)),
        make_cost=cost_breakdown.total_make_cost,
        fee_percentage=Decimal(str(channel.fee_percentage)),
        fee_fixed=Decimal(str(channel.fee_fixed)),
    )

    return ProductPricingResponse(
        id=pricing.id,
        product_id=pricing.product_id,
        sales_channel_id=pricing.sales_channel_id,
        list_price=pricing.list_price,
        is_active=pricing.is_active,
        channel_name=channel.name,
        platform_type=channel.platform_type,
        platform_fee=profit_data["platform_fee"],
        net_revenue=profit_data["net_revenue"],
        profit=profit_data["profit"],
        margin_percentage=profit_data["margin_percentage"],
        created_at=pricing.created_at,
        updated_at=pricing.updated_at,
    )


@router.delete("/{product_id}/pricing/{pricing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_product_pricing(
    product_id: UUID,
    pricing_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove product pricing for a sales channel.
    """
    query = (
        select(ProductPricing)
        .join(Product)
        .where(
            ProductPricing.id == pricing_id,
            ProductPricing.product_id == product_id,
            Product.tenant_id == tenant.id,
        )
    )

    result = await db.execute(query)
    pricing = result.scalar_one_or_none()

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found",
        )

    await db.delete(pricing)
    await db.commit()


# ==================== Product Components (Bundle Composition) Management ====================


async def _check_circular_reference(
    db: AsyncSession,
    parent_id: UUID,
    child_id: UUID,
    visited: set | None = None,
) -> bool:
    """
    Check if adding child_id as a component of parent_id would create a circular reference.

    Returns True if circular reference would be created, False otherwise.
    """
    if visited is None:
        visited = set()

    if parent_id == child_id:
        return True

    if child_id in visited:
        return True

    visited.add(child_id)

    # Check if parent_id appears anywhere in child's descendants
    query = select(ProductComponent).where(ProductComponent.parent_product_id == child_id)
    result = await db.execute(query)
    child_components = result.scalars().all()

    for component in child_components:
        if component.child_product_id == parent_id:
            return True
        if await _check_circular_reference(db, parent_id, component.child_product_id, visited):
            return True

    return False


@router.post(
    "/{product_id}/components",
    response_model=ProductComponentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_product_component(
    product_id: UUID,
    component_data: ProductComponentCreate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductComponentResponse:
    """
    Add a child product to this product (create a bundle/set).

    The child product's cost will be included in the parent product's total make cost.
    Circular references are not allowed (A cannot contain B if B contains A).
    """
    # Verify parent product exists and belongs to tenant
    parent_product = await db.get(Product, product_id)
    if not parent_product or parent_product.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Verify child product exists and belongs to tenant
    child_product = await db.get(Product, component_data.child_product_id)
    if not child_product or child_product.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Child product not found",
        )

    # Prevent self-reference
    if component_data.child_product_id == product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A product cannot contain itself",
        )

    # Check for circular references
    if await _check_circular_reference(db, product_id, component_data.child_product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adding this product would create a circular reference",
        )

    # Check if this child product is already in the parent
    existing = await db.execute(
        select(ProductComponent).where(
            ProductComponent.parent_product_id == product_id,
            ProductComponent.child_product_id == component_data.child_product_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product is already a component of the parent product",
        )

    # Create product component entry
    product_component = ProductComponent(
        parent_product_id=product_id,
        child_product_id=component_data.child_product_id,
        quantity=component_data.quantity,
    )

    db.add(product_component)
    await db.commit()
    await db.refresh(product_component)

    # Calculate child product cost
    # Need to load child product with its relationships for cost calculation
    query = (
        select(Product)
        .where(Product.id == component_data.child_product_id)
        .options(*_get_product_load_options())
    )
    result = await db.execute(query)
    child_product_loaded = result.scalar_one()

    child_cost = CostingService.calculate_product_cost(child_product_loaded)

    return ProductComponentResponse(
        id=product_component.id,
        parent_product_id=product_component.parent_product_id,
        child_product_id=product_component.child_product_id,
        quantity=product_component.quantity,
        child_product_name=child_product.name,
        child_product_sku=child_product.sku,
        child_product_cost=child_cost.total_make_cost,
        created_at=product_component.created_at,
    )


@router.put(
    "/{product_id}/components/{component_id}",
    response_model=ProductComponentResponse,
)
async def update_product_component(
    product_id: UUID,
    component_id: UUID,
    component_data: ProductComponentUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductComponentResponse:
    """
    Update a child product's quantity in the bundle.
    """
    # Fetch product component with related child product
    query = (
        select(ProductComponent)
        .join(Product, ProductComponent.parent_product_id == Product.id)
        .where(
            ProductComponent.id == component_id,
            ProductComponent.parent_product_id == product_id,
            Product.tenant_id == tenant.id,
        )
        .options(selectinload(ProductComponent.child_product))
    )

    result = await db.execute(query)
    product_component = result.scalar_one_or_none()

    if not product_component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product component not found",
        )

    product_component.quantity = component_data.quantity
    await db.commit()
    await db.refresh(product_component)

    # Calculate child product cost
    query = (
        select(Product)
        .where(Product.id == product_component.child_product_id)
        .options(*_get_product_load_options())
    )
    result = await db.execute(query)
    child_product_loaded = result.scalar_one()

    child_cost = CostingService.calculate_product_cost(child_product_loaded)

    return ProductComponentResponse(
        id=product_component.id,
        parent_product_id=product_component.parent_product_id,
        child_product_id=product_component.child_product_id,
        quantity=product_component.quantity,
        child_product_name=product_component.child_product.name,
        child_product_sku=product_component.child_product.sku,
        child_product_cost=child_cost.total_make_cost,
        created_at=product_component.created_at,
    )


@router.delete(
    "/{product_id}/components/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_product_component(
    product_id: UUID,
    component_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a child product from the bundle.
    """
    query = (
        select(ProductComponent)
        .join(Product, ProductComponent.parent_product_id == Product.id)
        .where(
            ProductComponent.id == component_id,
            ProductComponent.parent_product_id == product_id,
            Product.tenant_id == tenant.id,
        )
    )

    result = await db.execute(query)
    product_component = result.scalar_one_or_none()

    if not product_component:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product component not found",
        )

    await db.delete(product_component)
    await db.commit()


# ==================== Product Images Management ====================


@router.get("/{product_id}/images", response_model=ProductImageListResponse)
async def list_product_images(
    product_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductImageListResponse:
    """
    List all images for a product.
    """
    # Verify product exists and belongs to tenant
    product = await db.get(Product, product_id)
    if not product or product.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Get images ordered by display_order
    query = (
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.display_order)
    )
    result = await db.execute(query)
    images = result.scalars().all()

    return ProductImageListResponse(
        images=[ProductImageResponse.model_validate(img) for img in images],
        total=len(images),
    )


@router.post(
    "/{product_id}/images",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_product_image(
    product_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(..., description="Image file (JPEG, PNG, or WebP)"),
    alt_text: str = Query("", max_length=255, description="Alt text for accessibility"),
    image_storage: ImageStorage = Depends(get_image_storage),
) -> ProductImageResponse:
    """
    Upload an image for a product.

    Accepts JPEG, PNG, and WebP images up to 10MB.
    Automatically generates a thumbnail version.
    First image uploaded becomes the primary image.
    """
    # Verify product exists and belongs to tenant
    product = await db.get(Product, product_id)
    if not product or product.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Read file content
    content = await file.read()

    # Validate and save image
    try:
        storage_result = await image_storage.save_image(
            file_content=content,
            content_type=file.content_type or "application/octet-stream",
            product_id=str(product_id),
            original_filename=file.filename,
        )
    except ImageStorageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Get next display order
    max_order_query = select(func.coalesce(func.max(ProductImage.display_order), -1)).where(
        ProductImage.product_id == product_id
    )
    max_order = await db.scalar(max_order_query)
    next_order = (max_order or -1) + 1

    # Check if this is the first image (make it primary)
    count_query = select(func.count()).where(ProductImage.product_id == product_id)
    existing_count = await db.scalar(count_query)
    is_primary = existing_count == 0

    # Create image record
    image = ProductImage(
        tenant_id=tenant.id,
        product_id=product_id,
        image_url=storage_result["image_url"],
        thumbnail_url=storage_result["thumbnail_url"],
        alt_text=alt_text,
        display_order=next_order,
        is_primary=is_primary,
        original_filename=file.filename,
        file_size=storage_result["file_size"],
        content_type=storage_result["content_type"],
    )

    db.add(image)
    await db.commit()
    await db.refresh(image)

    return ProductImageResponse.model_validate(image)


@router.patch("/{product_id}/images/{image_id}", response_model=ProductImageResponse)
async def update_product_image(
    product_id: UUID,
    image_id: UUID,
    image_data: ProductImageUpdate,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductImageResponse:
    """
    Update image alt text or display order.
    """
    # Fetch image
    query = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
        ProductImage.tenant_id == tenant.id,
    )
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Update fields
    update_data = image_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(image, field, value)

    await db.commit()
    await db.refresh(image)

    return ProductImageResponse.model_validate(image)


@router.post("/{product_id}/images/{image_id}/set-primary", response_model=ProductImageResponse)
async def set_primary_image(
    product_id: UUID,
    image_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
) -> ProductImageResponse:
    """
    Set an image as the primary image for the product.
    Unsets any existing primary image.
    """
    # Fetch image
    query = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
        ProductImage.tenant_id == tenant.id,
    )
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Unset existing primary images (using Core for efficiency)
    await db.execute(
        ProductImage.__table__.update()
        .where(ProductImage.product_id == product_id)
        .where(ProductImage.is_primary == True)  # noqa: E712 - SQLAlchemy requires == not 'is'
        .values(is_primary=False)
    )

    # Expire the ORM object to pick up the Core update, then set as primary
    await db.refresh(image)
    image.is_primary = True
    await db.commit()
    await db.refresh(image)

    return ProductImageResponse.model_validate(image)


@router.delete("/{product_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image(
    product_id: UUID,
    image_id: UUID,
    user: CurrentUser,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    image_storage: ImageStorage = Depends(get_image_storage),
):
    """
    Delete a product image.
    If this was the primary image, the next image becomes primary.
    """
    # Fetch image
    query = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
        ProductImage.tenant_id == tenant.id,
    )
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    was_primary = image.is_primary
    image_url = image.image_url
    thumbnail_url = image.thumbnail_url

    # Delete from database
    await db.delete(image)
    await db.commit()

    # Delete from storage
    try:
        await image_storage.delete_image(image_url, thumbnail_url)
    except ImageStorageError:
        pass  # Log but don't fail if file deletion fails

    # If was primary, set next image as primary
    if was_primary:
        next_image_query = (
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.display_order)
            .limit(1)
        )
        next_result = await db.execute(next_image_query)
        next_image = next_result.scalar_one_or_none()
        if next_image:
            next_image.is_primary = True
            await db.commit()


@router.post("/{product_id}/images/{image_id}/rotate", response_model=ProductImageResponse)
async def rotate_product_image(
    product_id: UUID,
    image_id: UUID,
    degrees: int = Query(default=90, description="Rotation degrees (90, 180, or 270 clockwise)"),
    user: CurrentUser = None,
    tenant: CurrentTenant = None,
    db: AsyncSession = Depends(get_db),
    image_storage: ImageStorage = Depends(get_image_storage),
) -> ProductImageResponse:
    """
    Rotate an image clockwise by 90, 180, or 270 degrees.
    """
    # Validate degrees
    if degrees not in (90, 180, 270):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Degrees must be 90, 180, or 270",
        )

    # Fetch image
    query = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
        ProductImage.tenant_id == tenant.id,
    )
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    # Rotate the image files
    try:
        await image_storage.rotate_image(image.image_url, image.thumbnail_url, degrees)
    except ImageStorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Update the record to trigger updated_at timestamp change
    from datetime import datetime, timezone

    new_timestamp = datetime.now(timezone.utc)
    image.updated_at = new_timestamp
    db.add(image)  # Ensure it's tracked
    await db.commit()
    await db.refresh(image)

    return ProductImageResponse.model_validate(image)


# ==================== Etsy Sync ====================


@router.post("/{product_id}/sync/etsy", response_model=SyncToEtsyResponse)
async def sync_product_to_etsy(
    product_id: UUID,
    request: SyncToEtsyRequest = SyncToEtsyRequest(),
    db: AsyncSession = Depends(get_db),
    tenant: CurrentTenant = None,
    user: CurrentUser = None,
    _admin: RequireAdmin = None,
):
    """
    Sync a product to Etsy.

    Creates a new Etsy listing if one doesn't exist, or updates the existing listing.
    Batchivo is always the source of truth - sync overwrites Etsy data.

    Note: Full Etsy API integration pending. This endpoint prepares the listing
    data and creates a tracking record.
    """
    # Get product with all relationships needed for sync
    query = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant.id,
    ).options(
        selectinload(Product.images),
        selectinload(Product.pricing).selectinload(ProductPricing.sales_channel),
        selectinload(Product.external_listings),
    )
    result = await db.execute(query)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sync inactive product",
        )

    # Perform sync
    try:
        sync_service = EtsySyncService(db, tenant.id)
        success, message, listing = await sync_service.sync_product(product, force=request.force)

        await db.commit()

        return SyncToEtsyResponse(
            success=success,
            message=message,
            listing=ExternalListingResponse.model_validate(listing) if listing else None,
            etsy_url=listing.external_url if listing else None,
        )

    except EtsySyncError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
