"""Category management API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.category import Category, product_categories
from app.models.product import Product
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
    slugify,
)

router = APIRouter()


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive categories"),
    search: Optional[str] = Query(None, description="Search by name"),
):
    """List all categories for the tenant."""
    query = select(Category).where(Category.tenant_id == tenant.id)

    if not include_inactive:
        query = query.where(Category.is_active.is_(True))

    if search:
        query = query.where(Category.name.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Apply pagination and ordering
    query = (
        query.order_by(Category.display_order, Category.name)
        .offset((page - 1) * limit)
        .limit(limit)
    )

    result = await db.execute(query)
    categories = result.scalars().all()

    # Get product counts for each category
    category_responses = []
    for cat in categories:
        # Count products in this category
        count_result = await db.execute(
            select(func.count())
            .select_from(product_categories)
            .where(product_categories.c.category_id == cat.id)
        )
        product_count = count_result.scalar_one()

        category_responses.append(
            CategoryResponse(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                description=cat.description,
                display_order=cat.display_order,
                is_active=cat.is_active,
                product_count=product_count,
                created_at=cat.created_at,
                updated_at=cat.updated_at,
            )
        )

    return CategoryListResponse(categories=category_responses, total=total)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """Get a single category by ID."""
    result = await db.execute(
        select(Category).where(Category.id == category_id).where(Category.tenant_id == tenant.id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Get product count
    count_result = await db.execute(
        select(func.count())
        .select_from(product_categories)
        .where(product_categories.c.category_id == category.id)
    )
    product_count = count_result.scalar_one()

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        display_order=category.display_order,
        is_active=category.is_active,
        product_count=product_count,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    # Generate slug from name if not provided
    slug = category_data.slug if category_data.slug else slugify(category_data.name)

    # Check slug uniqueness within tenant
    existing = await db.execute(
        select(Category).where(Category.tenant_id == tenant.id).where(Category.slug == slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with slug '{slug}' already exists",
        )

    category = Category(
        tenant_id=tenant.id,
        name=category_data.name,
        slug=slug,
        description=category_data.description,
        display_order=category_data.display_order,
        is_active=category_data.is_active,
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        display_order=category.display_order,
        is_active=category.is_active,
        product_count=0,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update a category."""
    result = await db.execute(
        select(Category).where(Category.id == category_id).where(Category.tenant_id == tenant.id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Check slug uniqueness if being updated
    if category_data.slug and category_data.slug != category.slug:
        existing = await db.execute(
            select(Category)
            .where(Category.tenant_id == tenant.id)
            .where(Category.slug == category_data.slug)
            .where(Category.id != category_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category with slug '{category_data.slug}' already exists",
            )

    # Update fields
    update_data = category_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)

    # Get product count
    count_result = await db.execute(
        select(func.count())
        .select_from(product_categories)
        .where(product_categories.c.category_id == category.id)
    )
    product_count = count_result.scalar_one()

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        display_order=category.display_order,
        is_active=category.is_active,
        product_count=product_count,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    hard_delete: bool = Query(False, description="Permanently delete (default: soft delete)"),
):
    """Delete a category (soft delete by default)."""
    result = await db.execute(
        select(Category).where(Category.id == category_id).where(Category.tenant_id == tenant.id)
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    if hard_delete:
        await db.delete(category)
    else:
        category.is_active = False

    await db.commit()
    return None


# Product-Category assignment endpoints


@router.get("/{category_id}/products")
async def list_category_products(
    category_id: UUID,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """List products in a category."""
    # Verify category exists
    cat_result = await db.execute(
        select(Category).where(Category.id == category_id).where(Category.tenant_id == tenant.id)
    )
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Category not found")

    # Get products in this category
    query = (
        select(Product)
        .join(product_categories, Product.id == product_categories.c.product_id)
        .where(product_categories.c.category_id == category_id)
        .where(Product.tenant_id == tenant.id)
    )

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    return {
        "products": [{"id": str(p.id), "sku": p.sku, "name": p.name} for p in products],
        "total": total,
    }


@router.post("/{category_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_product_to_category(
    category_id: UUID,
    product_id: UUID,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Add a product to a category."""
    # Verify both exist in tenant
    cat_result = await db.execute(
        select(Category).where(Category.id == category_id).where(Category.tenant_id == tenant.id)
    )
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    prod_result = await db.execute(
        select(Product).where(Product.id == product_id).where(Product.tenant_id == tenant.id)
    )
    product = prod_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if already in category using direct DB query (avoids ORM instance comparison issues)
    from app.models.category import product_categories
    from sqlalchemy import select as sa_select

    existing = await db.execute(
        sa_select(product_categories).where(
            product_categories.c.product_id == product_id,
            product_categories.c.category_id == category_id,
        )
    )
    if existing.first() is not None:
        return None  # Already added, no-op

    # Use raw insert to include tenant_id for multi-tenant isolation
    await db.execute(
        product_categories.insert().values(
            tenant_id=tenant.id,
            product_id=product_id,
            category_id=category_id,
        )
    )
    await db.commit()
    return None


@router.delete("/{category_id}/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_product_from_category(
    category_id: UUID,
    product_id: UUID,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Remove a product from a category."""
    # Verify both exist in tenant
    cat_result = await db.execute(
        select(Category).where(Category.id == category_id).where(Category.tenant_id == tenant.id)
    )
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    prod_result = await db.execute(
        select(Product).where(Product.id == product_id).where(Product.tenant_id == tenant.id)
    )
    product = prod_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Use direct SQL delete to remove the association (avoids ORM instance comparison issues)
    from app.models.category import product_categories

    await db.execute(
        product_categories.delete().where(
            product_categories.c.product_id == product_id,
            product_categories.c.category_id == category_id,
        )
    )
    await db.commit()

    return None
