"""
Public shop API endpoints for multi-tenant storefronts.

These endpoints are public (no authentication required) and expose
product catalog, cart, and checkout functionality for the e-commerce frontend.

Tenant resolution is handled via X-Shop-Hostname header which identifies
the shop by subdomain (tenant.nozzly.shop) or custom domain.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import ShopContext, ShopTenant
from app.database import get_db
from app.models.category import Category, product_categories
from app.models.designer import Designer
from app.models.order import Order as OrderModel, OrderItem as OrderItemModel, OrderStatus
from app.models.product import Product
from app.models.review import Review
from app.services.cart import CartService, get_cart_service, CartItem
from app.services.checkout_session import CheckoutSessionService, get_checkout_session_service
from app.services.stock_reservation import (
    StockReservationService,
    get_stock_reservation_service,
    ReservationItem,
)
from app.services.shipping_service import ShippingService, get_shipping_service
from app.services.search_service import SearchService, get_search_service

router = APIRouter()

# ============================================
# Schemas
# ============================================


class ShopProductImage(BaseModel):
    """Product image for shop display."""

    url: str
    alt: str = ""
    is_primary: bool = False


class ShopProductCategory(BaseModel):
    """Category info for product display."""

    slug: str
    name: str


class ShopProductDesigner(BaseModel):
    """Designer info for product display."""

    id: str
    name: str
    slug: str


class ShopProduct(BaseModel):
    """Product response for shop display."""

    id: str
    sku: str
    name: str
    description: Optional[str] = None
    price: Decimal  # Price in pence
    currency: str = "GBP"
    images: list[ShopProductImage] = []
    categories: list[ShopProductCategory] = []
    designer: Optional[ShopProductDesigner] = None
    in_stock: bool = True
    print_to_order: bool = False  # Printed to order vs in-stock
    free_shipping: bool = False  # Qualifies for free shipping
    is_dragon: bool = False
    backstory: Optional[str] = None  # For dragons

    model_config = {"from_attributes": True}


class ShopProductList(BaseModel):
    """Paginated product list response."""

    data: list[ShopProduct]
    total: int
    page: int
    limit: int
    has_more: bool


class ShopCategory(BaseModel):
    """Category for shop navigation."""

    id: str
    name: str
    slug: str
    product_count: int = 0


# CartItem and Cart models are imported from app.services.cart


class AddToCartRequest(BaseModel):
    """Request to add item to cart."""

    product_id: str
    quantity: int = 1


class UpdateCartItemRequest(BaseModel):
    """Request to update cart item quantity."""

    quantity: int


class ShippingAddress(BaseModel):
    """Shipping address for checkout."""

    name: str
    email: str
    phone: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    county: Optional[str] = None
    postcode: str


class ShippingMethod(BaseModel):
    """Shipping method option."""

    id: str
    name: str
    description: str
    price: Decimal
    estimated_days: str


class CreateCheckoutRequest(BaseModel):
    """Request to create checkout session."""

    cart_session_id: str
    shippingAddress: ShippingAddress
    shippingMethodId: str
    discountCode: Optional[str] = None


class CheckoutSession(BaseModel):
    """Checkout session response."""

    sessionId: str
    orderTotal: Decimal
    squarePaymentFormUrl: Optional[str] = None


class CompleteCheckoutRequest(BaseModel):
    """Request to complete checkout with payment token."""

    payment_session_id: str
    square_payment_token: str


class Order(BaseModel):
    """Order response."""

    order_number: str
    status: str
    total: Decimal
    items: list[CartItem]
    shipping_address: ShippingAddress
    created_at: datetime


class ContactSubmission(BaseModel):
    """Contact form submission."""

    name: str
    email: str
    subject: str
    message: str
    order_number: Optional[str] = None


class ContactResponse(BaseModel):
    """Contact form response."""

    success: bool
    reference: str


class ApiResponse(BaseModel):
    """Generic API response wrapper."""

    data: Optional[dict | list] = None
    error: Optional[str] = None


# Cart storage is now handled by CartService (Redis-backed)
# Use get_cart_service() dependency for cart operations


# ============================================
# Product Endpoints
# ============================================


@router.get("/products", response_model=ShopProductList)
async def get_products(
    shop_context: ShopContext,
    category: Optional[str] = None,
    designer: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    search_service: SearchService = Depends(get_search_service),
):
    """
    Get products for shop display.

    Public endpoint - no authentication required.
    Tenant is resolved from X-Shop-Hostname header.
    Returns products with pricing from the tenant's online shop sales channel.

    Supports full-text search via the 'search' parameter.
    Supports filtering by category slug or designer slug.
    """
    shop_tenant, channel = shop_context

    # If search is provided, use full-text search
    if search:
        offset = (page - 1) * limit
        products, total = await search_service.search_products(
            query=search,
            tenant_id=shop_tenant.id,  # Filter by shop tenant
            shop_visible_only=True,
            active_only=True,
            limit=limit,
            offset=offset,
        )

        # Load relationships for the found products
        if products:
            product_ids = [p.id for p in products]
            query = (
                select(Product)
                .where(Product.id.in_(product_ids))
                .options(
                    selectinload(Product.pricing),
                    selectinload(Product.images),
                    selectinload(Product.categories),
                    selectinload(Product.designer),
                )
            )

            # Filter by category if also provided
            if category:
                query = (
                    query.join(product_categories, Product.id == product_categories.c.product_id)
                    .join(Category, Category.id == product_categories.c.category_id)
                    .where(Category.slug == category)
                    .where(Category.is_active.is_(True))
                )

            # Filter by designer if also provided
            if designer:
                query = (
                    query.join(Designer, Designer.id == Product.designer_id)
                    .where(Designer.slug == designer)
                    .where(Designer.is_active.is_(True))
                )

            result = await db.execute(query)
            products_with_rels = {p.id: p for p in result.scalars().all()}
            products = [products_with_rels[p.id] for p in products if p.id in products_with_rels]
            # If category or designer filter was applied, total might be different
            if category or designer:
                total = len(products)
    else:
        # Build query for products with pricing, images, categories, and designer
        # Filter by tenant and shop_visible (products explicitly marked for shop display)
        query = (
            select(Product)
            .options(
                selectinload(Product.pricing),
                selectinload(Product.images),
                selectinload(Product.categories),
                selectinload(Product.designer),
            )
            .where(Product.tenant_id == shop_tenant.id)
            .where(Product.is_active.is_(True))
            .where(Product.shop_visible.is_(True))
        )

        # Filter by category if provided (by slug)
        if category:
            query = (
                query.join(product_categories, Product.id == product_categories.c.product_id)
                .join(Category, Category.id == product_categories.c.category_id)
                .where(Category.slug == category)
                .where(Category.is_active.is_(True))
            )

        # Filter by designer if provided (by slug)
        if designer:
            query = (
                query.join(Designer, Designer.id == Product.designer_id)
                .where(Designer.slug == designer)
                .where(Designer.is_active.is_(True))
            )

        # Get total count (with same filters)
        count_query = select(Product).where(
            Product.tenant_id == shop_tenant.id,
            Product.is_active.is_(True),
            Product.shop_visible.is_(True),
        )
        if category:
            count_query = (
                count_query.join(product_categories, Product.id == product_categories.c.product_id)
                .join(Category, Category.id == product_categories.c.category_id)
                .where(Category.slug == category)
                .where(Category.is_active.is_(True))
            )
        if designer:
            count_query = (
                count_query.join(Designer, Designer.id == Product.designer_id)
                .where(Designer.slug == designer)
                .where(Designer.is_active.is_(True))
            )
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # Apply sorting
        if sort == "price-asc":
            query = query.order_by(Product.created_at.asc())
        elif sort == "price-desc":
            query = query.order_by(Product.created_at.desc())
        else:  # newest
            query = query.order_by(Product.created_at.desc())

        result = await db.execute(query)
        products = result.scalars().all()

    # Convert to shop products with pricing
    shop_products = []
    for product in products:
        # Find pricing for tenant's shop channel
        price = Decimal("0")
        if channel:
            for pricing in product.pricing:
                if pricing.sales_channel_id == channel.id:
                    price = pricing.list_price or Decimal("0")
                    break

        # If no channel-specific price, use first available
        if price == 0 and product.pricing:
            price = product.pricing[0].list_price or Decimal("0")

        # Check if it's a dragon item using dedicated is_dragon field
        is_dragon = getattr(product, "is_dragon", False)

        # Convert images to ShopProductImage format
        # Use /api/v1/shop/images/ endpoint to bypass ingress routing issues
        product_images = []
        for img in getattr(product, "images", []):
            # Convert /uploads/products/{id}/{filename} to /api/v1/shop/images/{id}/{filename}
            image_url = img.image_url
            if image_url.startswith("/uploads/products/"):
                image_url = image_url.replace("/uploads/products/", "/api/v1/shop/images/")
            product_images.append(
                ShopProductImage(
                    url=image_url,
                    alt=img.alt_text or "",
                    is_primary=img.is_primary,
                )
            )

        # Convert categories to ShopProductCategory format
        product_categories_list = [
            ShopProductCategory(slug=cat.slug, name=cat.name)
            for cat in getattr(product, "categories", [])
            if cat.is_active
        ]

        # Get designer info if available
        designer_info = None
        if product.designer and product.designer.is_active:
            designer_info = ShopProductDesigner(
                id=str(product.designer.id),
                name=product.designer.name,
                slug=product.designer.slug,
            )

        shop_product = ShopProduct(
            id=str(product.id),
            sku=product.sku or "",
            name=product.name,
            description=product.description,
            price=price * 100,  # Convert to pence
            images=product_images,
            categories=product_categories_list,
            designer=designer_info,
            in_stock=product.units_in_stock > 0,
            print_to_order=getattr(product, "print_to_order", False),
            free_shipping=getattr(product, "free_shipping", False),
            is_dragon=is_dragon,
        )
        shop_products.append(shop_product)

    return ShopProductList(
        data=shop_products,
        total=total,
        page=page,
        limit=limit,
        has_more=(page * limit) < total,
    )


@router.get("/products/{product_id}")
async def get_product(
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get single product details."""
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Product not found")

    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.pricing),
            selectinload(Product.images),
            selectinload(Product.categories),
            selectinload(Product.designer),
        )
        .where(Product.id == product_uuid)
        .where(Product.shop_visible.is_(True))
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get pricing
    price = Decimal("0")
    if product.pricing:
        price = product.pricing[0].list_price or Decimal("0")

    is_dragon = getattr(product, "is_dragon", False)

    # Convert images - use API endpoint for reliable delivery
    product_images = []
    for img in getattr(product, "images", []):
        image_url = img.image_url
        if image_url.startswith("/uploads/products/"):
            image_url = image_url.replace("/uploads/products/", "/api/v1/shop/images/")
        product_images.append(
            ShopProductImage(
                url=image_url,
                alt=img.alt_text or "",
                is_primary=img.is_primary,
            )
        )

    # Convert categories
    product_categories_list = [
        ShopProductCategory(slug=cat.slug, name=cat.name)
        for cat in getattr(product, "categories", [])
        if cat.is_active
    ]

    # Get designer info if available
    designer_info = None
    if product.designer and product.designer.is_active:
        designer_info = ShopProductDesigner(
            id=str(product.designer.id),
            name=product.designer.name,
            slug=product.designer.slug,
        )

    # Use shop_description if available, otherwise fall back to description
    display_description = getattr(product, "shop_description", None) or product.description

    # Use feature_title if available (for dragons), otherwise use name
    display_name = getattr(product, "feature_title", None) or product.name

    return {
        "data": ShopProduct(
            id=str(product.id),
            sku=product.sku or "",
            name=display_name,
            description=display_description,
            price=price * 100,
            images=product_images,
            categories=product_categories_list,
            designer=designer_info,
            in_stock=product.units_in_stock > 0,
            print_to_order=getattr(product, "print_to_order", False),
            free_shipping=getattr(product, "free_shipping", False),
            is_dragon=is_dragon,
            backstory=getattr(product, "backstory", None),
        )
    }


@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get product categories for shop navigation."""
    from sqlalchemy import func

    # Get all active categories with product counts
    result = await db.execute(
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.display_order, Category.name)
    )
    categories = result.scalars().all()

    # Build response with product counts
    category_list = []
    for cat in categories:
        # Count shop-visible products in this category
        count_result = await db.execute(
            select(func.count())
            .select_from(product_categories)
            .join(Product, Product.id == product_categories.c.product_id)
            .where(product_categories.c.category_id == cat.id)
            .where(Product.is_active.is_(True))
            .where(Product.shop_visible.is_(True))
        )
        product_count = count_result.scalar_one()

        category_list.append(
            ShopCategory(
                id=str(cat.id),
                name=cat.name,
                slug=cat.slug,
                product_count=product_count,
            )
        )

    return {"data": category_list}


@router.get("/designers")
async def get_designers(db: AsyncSession = Depends(get_db)):
    """
    Get active designers for shop display.

    Public endpoint - no authentication required.
    Returns designers with their product counts.
    """
    from sqlalchemy import func

    # Get all active designers
    result = await db.execute(
        select(Designer).where(Designer.is_active.is_(True)).order_by(Designer.name)
    )
    designers = result.scalars().all()

    # Build response with product counts
    designer_list = []
    for designer in designers:
        # Count shop-visible products for this designer
        count_result = await db.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.designer_id == designer.id)
            .where(Product.is_active.is_(True))
            .where(Product.shop_visible.is_(True))
        )
        product_count = count_result.scalar_one()

        designer_list.append(
            {
                "id": str(designer.id),
                "name": designer.name,
                "slug": designer.slug,
                "description": designer.description,
                "logo_url": designer.logo_url,
                "website_url": designer.website_url,
                "social_links": designer.social_links,
                "product_count": product_count,
            }
        )

    return {"data": designer_list}


@router.get("/designers/{slug}")
async def get_designer_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single designer by slug with their products.

    Public endpoint - no authentication required.
    """
    from sqlalchemy import func

    # Find designer by slug
    result = await db.execute(
        select(Designer).where(Designer.slug == slug).where(Designer.is_active.is_(True))
    )
    designer = result.scalar_one_or_none()

    if not designer:
        raise HTTPException(status_code=404, detail="Designer not found")

    # Get product count
    count_result = await db.execute(
        select(func.count())
        .select_from(Product)
        .where(Product.designer_id == designer.id)
        .where(Product.is_active.is_(True))
        .where(Product.shop_visible.is_(True))
    )
    product_count = count_result.scalar_one()

    return {
        "data": {
            "id": str(designer.id),
            "name": designer.name,
            "slug": designer.slug,
            "description": designer.description,
            "logo_url": designer.logo_url,
            "website_url": designer.website_url,
            "social_links": designer.social_links,
            "product_count": product_count,
        }
    }


@router.get("/dragons")
async def get_dragons(db: AsyncSession = Depends(get_db)):
    """Get dragon products for the Dragons collection page.

    Returns products where is_dragon=True. This is separate from is_featured
    which controls whether a product appears in the general showcase/gallery.
    """
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.pricing),
            selectinload(Product.images),
            selectinload(Product.categories),
            selectinload(Product.designer),
        )
        .where(Product.is_active.is_(True))
        .where(Product.shop_visible.is_(True))
        .where(Product.is_dragon.is_(True))
        .order_by(Product.created_at.desc())
    )
    products = result.scalars().all()

    shop_products = []
    for product in products:
        price = Decimal("0")
        if product.pricing:
            price = product.pricing[0].list_price or Decimal("0")

        # Convert images - use API endpoint for reliable delivery
        product_images = []
        for img in getattr(product, "images", []):
            image_url = img.image_url
            if image_url.startswith("/uploads/products/"):
                image_url = image_url.replace("/uploads/products/", "/api/v1/shop/images/")
            product_images.append(
                ShopProductImage(
                    url=image_url,
                    alt=img.alt_text or "",
                    is_primary=img.is_primary,
                )
            )

        # Convert categories
        product_categories_list = [
            ShopProductCategory(slug=cat.slug, name=cat.name)
            for cat in getattr(product, "categories", [])
            if cat.is_active
        ]

        # Get designer info if available
        designer_info = None
        if product.designer and product.designer.is_active:
            designer_info = ShopProductDesigner(
                id=str(product.designer.id),
                name=product.designer.name,
                slug=product.designer.slug,
            )

        # Use feature_title if available (e.g., dragon name), otherwise product name
        display_name = getattr(product, "feature_title", None) or product.name

        # Use shop_description if available, otherwise fall back to description
        display_description = getattr(product, "shop_description", None) or product.description

        shop_products.append(
            ShopProduct(
                id=str(product.id),
                sku=product.sku or "",
                name=display_name,
                description=display_description,
                price=price * 100,
                images=product_images,
                categories=product_categories_list,
                designer=designer_info,
                in_stock=product.units_in_stock > 0,
                print_to_order=getattr(product, "print_to_order", False),
                free_shipping=getattr(product, "free_shipping", False),
                is_dragon=True,
                backstory=getattr(product, "backstory", None),
            )
        )

    return {"data": shop_products}


# ============================================
# Cart Endpoints
# ============================================


@router.get("/cart/{session_id}")
async def get_cart_endpoint(session_id: str, cart_service: CartService = Depends(get_cart_service)):
    """Get cart for session."""
    cart = await cart_service.get_cart(session_id)
    return {"data": cart}


@router.post("/cart")
async def create_cart(request: dict, cart_service: CartService = Depends(get_cart_service)):
    """Create new cart."""
    session_id = request.get("session_id") or str(uuid4())
    cart = await cart_service.get_cart(session_id)
    return {"data": cart}


@router.post("/cart/{session_id}/items")
async def add_to_cart(
    session_id: str,
    request: AddToCartRequest,
    db: AsyncSession = Depends(get_db),
    cart_service: CartService = Depends(get_cart_service),
    reservation_service: StockReservationService = Depends(get_stock_reservation_service),
):
    """Add item to cart."""
    # Get product details
    try:
        product_uuid = UUID(request.product_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Product not found")

    result = await db.execute(
        select(Product).options(selectinload(Product.pricing)).where(Product.id == product_uuid)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check stock availability (including reservations) for non print-to-order items
    is_print_to_order = getattr(product, "print_to_order", False)
    if not is_print_to_order:
        stock_info = await reservation_service.get_available_stock(request.product_id, db)

        # Get current cart to check if we already have this item
        current_cart = await cart_service.get_cart(session_id)
        existing_quantity = 0
        for item in current_cart.items:
            if item.product_id == request.product_id:
                existing_quantity = item.quantity
                break

        total_requested = existing_quantity + request.quantity
        if total_requested > stock_info.available_stock:
            if stock_info.available_stock <= 0:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "out_of_stock",
                        "message": f"{product.name} is currently out of stock",
                    },
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "insufficient_stock",
                        "message": f"Only {stock_info.available_stock} of {product.name} available",
                        "available": stock_info.available_stock,
                    },
                )

    # Get price
    price = Decimal("0")
    if product.pricing:
        price = product.pricing[0].list_price or Decimal("0")
    price_pence = price * 100

    # Add to cart via service
    cart = await cart_service.add_item(
        session_id=session_id,
        product_id=request.product_id,
        product_name=product.name,
        product_sku=product.sku or "",
        quantity=request.quantity,
        unit_price=price_pence,
    )

    return {"data": cart}


@router.delete("/cart/{session_id}/items/{item_id}")
async def remove_from_cart(
    session_id: str,
    item_id: str,
    cart_service: CartService = Depends(get_cart_service),
):
    """Remove item from cart."""
    cart = await cart_service.remove_item(session_id, item_id)
    return {"data": cart}


@router.patch("/cart/{session_id}/items/{item_id}")
async def update_cart_item(
    session_id: str,
    item_id: str,
    request: UpdateCartItemRequest,
    cart_service: CartService = Depends(get_cart_service),
):
    """Update cart item quantity."""
    cart = await cart_service.update_item(session_id, item_id, request.quantity)
    return {"data": cart}


# ============================================
# Checkout Endpoints
# ============================================


@router.post("/checkout/shipping-rates")
async def get_checkout_shipping_rates(
    request: dict,
    shipping_service: ShippingService = Depends(get_shipping_service),
):
    """Get shipping rates for postcode.

    Uses the shipping service for postcode validation and rate calculation.
    Applies Highland/Island surcharges for remote UK areas.
    """
    postcode = request.get("postcode", "")
    cart_total_pence = request.get("cart_total_pence")

    # Get rates from shipping service
    rates_response = await shipping_service.get_shipping_rates(
        postcode=postcode,
        cart_total_pence=cart_total_pence,
    )

    # Convert to legacy format for frontend compatibility
    legacy_rates = [
        ShippingMethod(
            id=opt.id,
            name=opt.name,
            description=opt.description,
            price=Decimal(str(opt.price_pence)),  # Keep in pence for frontend
            estimated_days=opt.estimated_days_display,
        )
        for opt in rates_response.options
    ]

    return {
        "data": legacy_rates,
        "postcode_valid": rates_response.postcode_valid,
        "free_shipping_threshold": rates_response.free_shipping_threshold_pence,
        "qualifies_for_free_shipping": rates_response.qualifies_for_free_shipping,
    }


class ValidateDiscountRequest(BaseModel):
    """Request to validate a discount code."""

    code: str
    subtotal: Decimal  # Subtotal in pounds (not pence)
    customer_email: Optional[str] = None


class ValidateDiscountResponse(BaseModel):
    """Response from discount validation."""

    valid: bool
    code: str
    discount_type: Optional[str] = None
    discount_amount: Decimal = Decimal("0")  # Discount in pounds
    message: str


@router.post("/checkout/validate-discount", response_model=ValidateDiscountResponse)
async def validate_discount(
    request: ValidateDiscountRequest,
    shop_context: ShopContext,
    db: AsyncSession = Depends(get_db),
):
    """
    Validate a discount code for checkout.

    Public endpoint - tenant resolved from X-Shop-Hostname header.
    Returns whether the code is valid and the calculated discount amount.
    """
    from app.api.v1.discounts import validate_discount_code
    from app.schemas.discount import DiscountValidationRequest

    shop_tenant, _ = shop_context

    # Convert to internal validation request
    validation_request = DiscountValidationRequest(
        code=request.code.upper().strip(),
        subtotal=request.subtotal,
        customer_email=request.customer_email,
    )

    # Validate using existing discount validation logic
    validation_response = await validate_discount_code(
        data=validation_request,
        db=db,
        tenant=shop_tenant,
    )

    return ValidateDiscountResponse(
        valid=validation_response.valid,
        code=request.code.upper().strip(),
        discount_type=validation_response.discount_type.value
        if validation_response.discount_type
        else None,
        discount_amount=validation_response.discount_amount or Decimal("0"),
        message=validation_response.message or "",
    )


@router.post("/checkout/create-payment")
async def create_checkout_session(
    request: CreateCheckoutRequest,
    shop_context: ShopContext,
    db: AsyncSession = Depends(get_db),
    cart_service: CartService = Depends(get_cart_service),
    checkout_service: CheckoutSessionService = Depends(get_checkout_session_service),
    reservation_service: StockReservationService = Depends(get_stock_reservation_service),
    shipping_service: ShippingService = Depends(get_shipping_service),
):
    """Create checkout/payment session with stock reservation. Tenant from X-Shop-Hostname."""
    shop_tenant, channel = shop_context
    cart = await cart_service.get_cart(request.cart_session_id)

    if not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Calculate totals
    subtotal = cart.subtotal

    # Get shipping cost from shipping service (with postcode-aware pricing)
    postcode = request.shippingAddress.postcode
    cart_total_pence = int(subtotal * 100)  # Convert to pence for free shipping check
    shipping_method_name, shipping_cost_pence = shipping_service.get_shipping_cost(
        shipping_method_id=request.shippingMethodId,
        postcode=postcode,
        cart_total_pence=cart_total_pence,
    )
    shipping_cost = Decimal(str(shipping_cost_pence))

    # Handle discount code if provided
    discount_code = None
    discount_amount = Decimal("0")

    if request.discountCode:
        from app.api.v1.discounts import validate_discount_code
        from app.schemas.discount import DiscountValidationRequest

        # Validate discount code using resolved shop tenant
        validation_request = DiscountValidationRequest(
            code=request.discountCode,
            subtotal=subtotal / 100,  # Convert from pence to pounds for validation
            customer_email=request.shippingAddress.email,
        )

        validation_response = await validate_discount_code(
            data=validation_request,
            db=db,
            tenant=shop_tenant,
        )

        if validation_response.valid:
            discount_code = request.discountCode.upper().strip()
            # Convert discount amount from pounds to pence
            discount_amount = validation_response.discount_amount * 100

    total = subtotal + shipping_cost - discount_amount

    # Reserve stock for cart items (prevents overselling)
    reservation_items = [
        ReservationItem(
            product_id=item.product_id,
            quantity=item.quantity,
            product_name=item.product_name,
            product_sku=item.product_sku,
        )
        for item in cart.items
    ]

    reservation_result = await reservation_service.reserve_stock(
        session_id=request.cart_session_id,  # Use cart session as reservation key
        items=reservation_items,
        db=db,
    )

    if not reservation_result.success:
        # Build detailed error message
        failed_details = []
        for failed in reservation_result.failed_items:
            if failed.get("available") is not None:
                failed_details.append(
                    f"{failed.get('product_name', failed['product_id'])}: "
                    f"only {failed['available']} available, need {failed['requested']}"
                )
            else:
                failed_details.append(
                    f"{failed.get('product_name', failed['product_id'])}: {failed['reason']}"
                )

        raise HTTPException(
            status_code=400,
            detail={
                "error": "insufficient_stock",
                "message": "Some items in your cart are no longer available in the requested quantity",
                "items": failed_details,
            },
        )

    # Create checkout session in Redis
    session_id = await checkout_service.create_session(
        cart_session_id=request.cart_session_id,
        shipping_address=request.shippingAddress.model_dump(),
        shipping_method_id=request.shippingMethodId,
        shipping_method_name=shipping_method_name,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        discount_code=discount_code,
        discount_amount=discount_amount,
        total=total,
    )

    return {
        "data": CheckoutSession(
            sessionId=session_id,
            orderTotal=total,
        )
    }


@router.post("/checkout/complete")
async def complete_checkout(
    request: CompleteCheckoutRequest,
    shop_context: ShopContext,
    db: AsyncSession = Depends(get_db),
    cart_service: CartService = Depends(get_cart_service),
    checkout_service: CheckoutSessionService = Depends(get_checkout_session_service),
    reservation_service: StockReservationService = Depends(get_stock_reservation_service),
):
    """Complete checkout with payment. Tenant resolved from X-Shop-Hostname header."""
    shop_tenant, channel = shop_context
    from app.schemas.payment import (
        PaymentRequest,
        CustomerDetails,
        ShippingAddress as PaymentShippingAddress,
        CartItem as PaymentCartItem,
    )
    from app.services.square_payment import get_payment_service

    session = await checkout_service.get_session(request.payment_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Checkout session not found")

    cart = await cart_service.get_cart(session.cart_session_id)
    shipping = session.shipping_address

    # Build payment request
    name_parts = shipping["name"].split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    payment_request = PaymentRequest(
        payment_token=request.square_payment_token,
        amount=int(session.total),  # Already in pence
        currency="GBP",
        customer=CustomerDetails(
            email=shipping["email"],
            phone=shipping.get("phone"),
        ),
        shipping_address=PaymentShippingAddress(
            address_line1=shipping["line1"],
            address_line2=shipping.get("line2"),
            city=shipping["city"],
            county=shipping.get("county"),
            postcode=shipping["postcode"],
            country="GB",
            first_name=first_name,
            last_name=last_name,
        ),
        shipping_method=session.shipping_method_id,
        items=[
            PaymentCartItem(
                product_id=UUID(item.product_id),
                name=item.product_name,
                quantity=item.quantity,
                price=int(item.unit_price),
            )
            for item in cart.items
        ],
        shipping_cost=int(session.shipping_cost),
    )

    # Process payment
    payment_service = get_payment_service()
    result = payment_service.process_payment(payment_request)

    if not result.success:
        # Record payment failure metric
        try:
            from app.observability.metrics import record_payment_processed, record_error

            record_payment_processed(
                tenant_id="",  # Unknown at this point
                amount=float(session.total) / 100,
                status="failed",
                provider="square",
            )
            record_error(
                error_type="payment_failed",
                endpoint="/api/v1/shop/checkout/complete",
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=402,
            detail={
                "error_code": result.error_code,
                "error_message": result.error_message,
            },
        )

    # Generate order number using tenant's order prefix (PREFIX-YYYYMMDD-XXX format)
    # Get order prefix from tenant settings, fallback to uppercase slug
    settings = shop_tenant.settings or {}
    shop_settings = settings.get("shop", {})
    order_prefix = shop_settings.get("order_prefix") or shop_tenant.slug.upper()[:4]

    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    order_count_result = await db.execute(
        select(OrderModel).where(
            OrderModel.tenant_id == shop_tenant.id,
            OrderModel.order_number.like(f"{order_prefix}-{today}-%"),
        )
    )
    existing_orders = order_count_result.scalars().all()
    order_seq = len(existing_orders) + 1
    order_number = f"{order_prefix}-{today}-{order_seq:03d}"

    # Channel already resolved from ShopContext dependency

    # Create order in database using resolved tenant
    db_order = OrderModel(
        tenant_id=shop_tenant.id,
        order_number=order_number,
        sales_channel_id=channel.id,
        status=OrderStatus.PENDING,
        customer_email=shipping["email"],
        customer_name=shipping["name"],
        customer_phone=shipping.get("phone"),
        shipping_address_line1=shipping["line1"],
        shipping_address_line2=shipping.get("line2"),
        shipping_city=shipping["city"],
        shipping_county=shipping.get("county"),
        shipping_postcode=shipping["postcode"],
        shipping_country="United Kingdom",
        shipping_method=session.shipping_method_name,
        shipping_cost=Decimal(str(session.shipping_cost)) / 100,  # Convert from pence
        subtotal=Decimal(str(session.subtotal)) / 100,  # Convert from pence
        discount_code=session.discount_code,
        discount_amount=Decimal(str(session.discount_amount)) / 100,  # Convert from pence
        total=Decimal(str(session.total)) / 100,  # Convert from pence
        payment_provider="square",
        payment_id=result.payment_id,
        payment_status="completed",
    )
    db.add(db_order)

    # Create order items
    for item in cart.items:
        db_item = OrderItemModel(
            order_id=db_order.id,
            product_id=UUID(item.product_id) if item.product_id else None,
            product_sku=item.product_sku or "UNKNOWN",
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=Decimal(str(item.unit_price)) / 100,  # Convert from pence
            total_price=Decimal(str(item.unit_price * item.quantity)) / 100,
        )
        db.add(db_item)

    # Deduct inventory for each item
    for item in cart.items:
        if item.product_id:
            product_result = await db.execute(
                select(Product).where(Product.id == UUID(item.product_id))
            )
            product = product_result.scalar_one_or_none()
            if product and product.units_in_stock is not None:
                product.units_in_stock = max(0, product.units_in_stock - item.quantity)

    await db.commit()
    await db.refresh(db_order)

    # Record discount usage if a discount was applied
    if session.discount_code and session.discount_amount > 0:
        try:
            from app.api.v1.discounts import record_discount_usage, get_discount_code_by_code

            discount_code_record = await get_discount_code_by_code(
                db=db,
                tenant_id=channel.tenant_id,
                code=session.discount_code,
            )
            if discount_code_record:
                await record_discount_usage(
                    db=db,
                    tenant_id=channel.tenant_id,
                    discount_code_id=discount_code_record.id,
                    order_id=db_order.id,
                    customer_email=shipping["email"],
                    discount_amount=Decimal(str(session.discount_amount)) / 100,
                )
                await db.commit()
        except Exception as e:
            # Log but don't fail order for discount tracking errors
            import logging as discount_logging

            discount_logging.getLogger(__name__).error(f"Failed to record discount usage: {e}")

    # Record order and payment metrics
    try:
        from app.observability.metrics import record_order_created, record_payment_processed

        record_order_created(
            tenant_id=str(shop_tenant.id),
            total_amount=float(session.total) / 100,  # Convert from pence to pounds
            channel=shop_tenant.slug,
        )
        record_payment_processed(
            tenant_id=str(shop_tenant.id),
            amount=float(session.total) / 100,
            status="success",
            provider="square",
        )
    except Exception:
        pass  # Don't fail order for metrics errors

    # Send order confirmation email
    try:
        from app.services.email_service import get_email_service

        email_service = get_email_service()
        email_service.send_order_confirmation(
            to_email=shipping["email"],
            customer_name=shipping["name"],
            order_number=db_order.order_number,
            order_items=[
                {
                    "name": item.product_name,
                    "quantity": item.quantity,
                    "price": float(item.unit_price) / 100,
                }
                for item in cart.items
            ],
            subtotal=float(session.subtotal) / 100,
            shipping_cost=float(session.shipping_cost) / 100,
            total=float(session.total) / 100,
            shipping_address={
                "address_line1": shipping["line1"],
                "address_line2": shipping.get("line2"),
                "city": shipping["city"],
                "county": shipping.get("county"),
                "postcode": shipping["postcode"],
                "country": "United Kingdom",
            },
            receipt_url=result.receipt_url if hasattr(result, "receipt_url") else None,
        )
        # Track that confirmation email was sent
        db_order.confirmation_email_sent = True
        db_order.confirmation_email_sent_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as e:
        # Log but don't fail order for email errors
        import logging

        logging.getLogger(__name__).error(f"Failed to send order confirmation email: {e}")

    # Create order response
    order = Order(
        order_number=db_order.order_number,
        status="confirmed",
        total=session.total,
        items=cart.items,
        shipping_address=ShippingAddress(**shipping),
        created_at=db_order.created_at,
    )

    # Confirm stock reservation (releases temporary hold - stock already deducted)
    await reservation_service.confirm_reservation(session.cart_session_id)

    # Clear cart from Redis
    await cart_service.clear_cart(session.cart_session_id)

    # Clean up checkout session from Redis
    await checkout_service.delete_session(request.payment_session_id)

    return {"data": order}


# ============================================
# Order Endpoints
# ============================================


class PublicOrderItem(BaseModel):
    """Order item for public display."""

    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class PublicOrder(BaseModel):
    """Public order response (limited info for security)."""

    order_number: str
    status: str
    customer_name: str
    shipping_method: str
    shipping_cost: Decimal
    subtotal: Decimal
    total: Decimal
    items: list[PublicOrderItem]
    created_at: datetime
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


@router.get("/orders/{order_number}")
async def get_order(
    order_number: str,
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """Get order by number and email (for verification)."""
    # Find order with matching order_number and email
    result = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(
            OrderModel.order_number == order_number,
            OrderModel.customer_email == email.lower().strip(),
        )
    )
    db_order = result.scalar_one_or_none()

    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "data": PublicOrder(
            order_number=db_order.order_number,
            status=db_order.status.value,
            customer_name=db_order.customer_name,
            shipping_method=db_order.shipping_method or "Standard",
            shipping_cost=db_order.shipping_cost,
            subtotal=db_order.subtotal,
            total=db_order.total,
            items=[
                PublicOrderItem(
                    product_name=item.product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                )
                for item in db_order.items
            ],
            created_at=db_order.created_at,
            tracking_number=db_order.tracking_number,
            tracking_url=db_order.tracking_url,
            shipped_at=db_order.shipped_at,
            delivered_at=db_order.delivered_at,
        )
    }


# ============================================
# Image Proxy Endpoint
# ============================================


@router.get("/images/{product_id}/{image_filename}")
async def get_product_image(product_id: str, image_filename: str):
    """
    Serve product images through the API.

    This endpoint proxies image requests through /api/v1/shop/images/
    and works with both local storage and S3/MinIO.
    """
    from app.services.image_storage import get_image_storage, ImageStorageError

    storage = get_image_storage()
    image_url = f"/uploads/products/{product_id}/{image_filename}"

    try:
        content, content_type = await storage.get_image(image_url)
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )
    except ImageStorageError:
        raise HTTPException(status_code=404, detail="Image not found")


# ============================================
# Contact Endpoint
# ============================================


@router.post("/contact")
async def submit_contact(submission: ContactSubmission):
    """Submit contact form and send email notifications."""
    reference = f"MF-{uuid4().hex[:8].upper()}"

    # Send email notification (don't fail the request if email fails)
    try:
        from app.services.email_service import get_email_service

        email_service = get_email_service()
        email_service.send_contact_notification(
            name=submission.name,
            email=submission.email,
            subject=submission.subject,
            message=submission.message,
            reference=reference,
            order_number=submission.order_number,
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to send contact notification: {e}")
        # Don't raise - form submission still succeeded

    return {
        "data": ContactResponse(
            success=True,
            reference=reference,
        )
    }


# ============================================
# Pages Endpoint (Policy pages, etc.)
# ============================================


class ShopPage(BaseModel):
    """Public page response for shop."""

    slug: str
    title: str
    content: str
    meta_description: Optional[str] = None
    updated_at: datetime


@router.get("/pages/{slug}")
async def get_public_page(
    slug: str,
    shop_tenant: ShopTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a published page by slug.

    Used by the shop frontend for policy pages like privacy-policy, terms, etc.
    Only returns published pages. Tenant resolved from X-Shop-Hostname header.
    """
    from app.models.page import Page

    result = await db.execute(
        select(Page)
        .where(Page.tenant_id == shop_tenant.id)
        .where(Page.slug == slug)
        .where(Page.is_published.is_(True))
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    return {
        "data": ShopPage(
            slug=page.slug,
            title=page.title,
            content=page.content,
            meta_description=page.meta_description,
            updated_at=page.updated_at,
        )
    }


@router.get("/pages")
async def list_public_pages(
    shop_tenant: ShopTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    List all published pages.

    Used by the shop frontend to build navigation or footer links.
    Tenant resolved from X-Shop-Hostname header.
    """
    from app.models.page import Page

    result = await db.execute(
        select(Page)
        .where(Page.tenant_id == shop_tenant.id)
        .where(Page.is_published.is_(True))
        .order_by(Page.sort_order, Page.title)
    )
    pages = result.scalars().all()

    return {
        "data": [
            ShopPage(
                slug=p.slug,
                title=p.title,
                content=p.content,
                meta_description=p.meta_description,
                updated_at=p.updated_at,
            )
            for p in pages
        ]
    }


# ============================================
# Review Schemas
# ============================================


class ShopReviewCreate(BaseModel):
    """Request to submit a review."""

    rating: int = Field(..., ge=1, le=5, description="Star rating (1-5)")
    title: Optional[str] = Field(None, max_length=200, description="Review title")
    body: str = Field(..., min_length=10, max_length=5000, description="Review text")
    customer_name: str = Field(..., min_length=1, max_length=255, description="Display name")
    customer_email: EmailStr = Field(..., description="Email for verification")


class ShopReview(BaseModel):
    """Public review display."""

    id: str
    rating: int
    title: Optional[str]
    body: str
    customer_name: str
    is_verified_purchase: bool
    helpful_count: int
    created_at: datetime


class ShopReviewList(BaseModel):
    """Review list response with stats."""

    data: list[ShopReview]
    total: int
    average_rating: Optional[Decimal]
    rating_distribution: dict[int, int]  # {1: 5, 2: 10, ...}


class ShopReviewSubmitResponse(BaseModel):
    """Response after submitting a review."""

    success: bool
    message: str


# ============================================
# Review Endpoints
# ============================================


@router.get("/products/{product_id}/reviews", response_model=ShopReviewList)
async def get_product_reviews(
    product_id: str,
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Get approved reviews for a product.

    Public endpoint - no authentication required.
    Only returns approved reviews.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Product not found")

    # Verify product exists and is visible
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_uuid,
            Product.shop_visible.is_(True),
        )
    )
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get approved reviews with pagination
    offset = (page - 1) * limit
    reviews_query = (
        select(Review)
        .where(
            Review.product_id == product_uuid,
            Review.is_approved.is_(True),
        )
        .order_by(desc(Review.created_at))
        .offset(offset)
        .limit(limit)
    )
    reviews_result = await db.execute(reviews_query)
    reviews = reviews_result.scalars().all()

    # Get total count
    count_query = select(func.count(Review.id)).where(
        Review.product_id == product_uuid,
        Review.is_approved.is_(True),
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get rating distribution
    distribution_query = (
        select(Review.rating, func.count(Review.id))
        .where(
            Review.product_id == product_uuid,
            Review.is_approved.is_(True),
        )
        .group_by(Review.rating)
    )
    distribution_result = await db.execute(distribution_query)
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for rating, count in distribution_result.all():
        rating_distribution[rating] = count

    # Get average rating
    avg_query = select(func.avg(Review.rating)).where(
        Review.product_id == product_uuid,
        Review.is_approved.is_(True),
    )
    avg_result = await db.execute(avg_query)
    average_rating = avg_result.scalar()
    if average_rating:
        average_rating = round(Decimal(str(average_rating)), 2)

    return ShopReviewList(
        data=[
            ShopReview(
                id=str(r.id),
                rating=r.rating,
                title=r.title,
                body=r.body,
                customer_name=r.customer_name,
                is_verified_purchase=r.is_verified_purchase,
                helpful_count=r.helpful_count,
                created_at=r.created_at,
            )
            for r in reviews
        ],
        total=total,
        average_rating=average_rating,
        rating_distribution=rating_distribution,
    )


@router.post("/products/{product_id}/reviews", response_model=ShopReviewSubmitResponse)
async def submit_product_review(
    product_id: str,
    review: ShopReviewCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a review for a product.

    Public endpoint - no authentication required.
    Reviews require admin approval before they appear publicly.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Product not found")

    # Verify product exists and is visible
    product_result = await db.execute(
        select(Product).where(
            Product.id == product_uuid,
            Product.shop_visible.is_(True),
        )
    )
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if this email has already reviewed this product
    existing_review = await db.execute(
        select(Review).where(
            Review.product_id == product_uuid,
            func.lower(Review.customer_email) == review.customer_email.lower(),
        )
    )
    if existing_review.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="You have already submitted a review for this product",
        )

    # Check if this is a verified purchase
    is_verified_purchase = False
    order_id = None
    order_check = await db.execute(
        select(OrderModel)
        .options(selectinload(OrderModel.items))
        .where(
            func.lower(OrderModel.customer_email) == review.customer_email.lower(),
            OrderModel.tenant_id == product.tenant_id,
        )
    )
    orders = order_check.scalars().all()
    for order in orders:
        for item in order.items:
            if item.product_id == product_uuid:
                is_verified_purchase = True
                order_id = order.id
                break
        if is_verified_purchase:
            break

    # Create the review (pending approval)
    new_review = Review(
        tenant_id=product.tenant_id,
        product_id=product_uuid,
        customer_email=review.customer_email.lower(),
        customer_name=review.customer_name,
        rating=review.rating,
        title=review.title,
        body=review.body,
        is_verified_purchase=is_verified_purchase,
        order_id=order_id,
        is_approved=False,  # Requires admin approval
    )
    db.add(new_review)
    await db.commit()

    return ShopReviewSubmitResponse(
        success=True,
        message="Thank you for your review! It will be visible after approval.",
    )


@router.post("/products/{product_id}/reviews/{review_id}/helpful")
async def mark_review_helpful(
    product_id: str,
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a review as helpful.

    Public endpoint - increments the helpful count.
    Note: No rate limiting in this simple implementation.
    """
    try:
        review_uuid = UUID(review_id)
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Review not found")

    # Find the approved review
    result = await db.execute(
        select(Review).where(
            Review.id == review_uuid,
            Review.product_id == product_uuid,
            Review.is_approved.is_(True),
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Increment helpful count
    review.helpful_count += 1
    await db.commit()

    return {
        "data": {
            "review_id": str(review.id),
            "helpful_count": review.helpful_count,
        }
    }
