"""Designer management API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.designer import Designer
from app.models.product import Product
from app.schemas.designer import (
    DesignerCreate,
    DesignerListResponse,
    DesignerResponse,
    DesignerUpdate,
    slugify,
)

router = APIRouter()


@router.get("", response_model=DesignerListResponse)
async def list_designers(
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive designers"),
    search: Optional[str] = Query(None, description="Search by name"),
):
    """List all designers for the tenant."""
    query = select(Designer).where(Designer.tenant_id == tenant.id)

    if not include_inactive:
        query = query.where(Designer.is_active.is_(True))

    if search:
        query = query.where(Designer.name.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Apply pagination and ordering
    query = query.order_by(Designer.name).offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    designers = result.scalars().all()

    # Get product counts for each designer
    designer_responses = []
    for designer in designers:
        # Count products for this designer
        count_result = await db.execute(
            select(func.count()).select_from(Product).where(Product.designer_id == designer.id)
        )
        product_count = count_result.scalar_one()

        designer_responses.append(
            DesignerResponse(
                id=designer.id,
                name=designer.name,
                slug=designer.slug,
                description=designer.description,
                logo_url=designer.logo_url,
                website_url=designer.website_url,
                social_links=designer.social_links,
                membership_cost=designer.membership_cost,
                membership_start_date=designer.membership_start_date,
                membership_renewal_date=designer.membership_renewal_date,
                is_active=designer.is_active,
                notes=designer.notes,
                product_count=product_count,
                created_at=designer.created_at,
                updated_at=designer.updated_at,
            )
        )

    return DesignerListResponse(designers=designer_responses, total=total)


@router.get("/{designer_id}", response_model=DesignerResponse)
async def get_designer(
    designer_id: UUID,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """Get a single designer by ID."""
    result = await db.execute(
        select(Designer).where(Designer.id == designer_id).where(Designer.tenant_id == tenant.id)
    )
    designer = result.scalar_one_or_none()

    if not designer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designer not found",
        )

    # Get product count
    count_result = await db.execute(
        select(func.count()).select_from(Product).where(Product.designer_id == designer.id)
    )
    product_count = count_result.scalar_one()

    return DesignerResponse(
        id=designer.id,
        name=designer.name,
        slug=designer.slug,
        description=designer.description,
        logo_url=designer.logo_url,
        website_url=designer.website_url,
        social_links=designer.social_links,
        membership_cost=designer.membership_cost,
        membership_start_date=designer.membership_start_date,
        membership_renewal_date=designer.membership_renewal_date,
        is_active=designer.is_active,
        notes=designer.notes,
        product_count=product_count,
        created_at=designer.created_at,
        updated_at=designer.updated_at,
    )


@router.post("", response_model=DesignerResponse, status_code=status.HTTP_201_CREATED)
async def create_designer(
    designer_data: DesignerCreate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new designer."""
    # Generate slug from name if not provided
    slug = designer_data.slug if designer_data.slug else slugify(designer_data.name)

    # Check slug uniqueness within tenant
    existing = await db.execute(
        select(Designer).where(Designer.tenant_id == tenant.id).where(Designer.slug == slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Designer with slug '{slug}' already exists",
        )

    # Create designer
    designer = Designer(
        tenant_id=tenant.id,
        name=designer_data.name,
        slug=slug,
        description=designer_data.description,
        logo_url=designer_data.logo_url,
        website_url=designer_data.website_url,
        social_links=designer_data.social_links,
        membership_cost=designer_data.membership_cost,
        membership_start_date=designer_data.membership_start_date,
        membership_renewal_date=designer_data.membership_renewal_date,
        is_active=designer_data.is_active,
        notes=designer_data.notes,
    )

    db.add(designer)
    await db.commit()
    await db.refresh(designer)

    return DesignerResponse(
        id=designer.id,
        name=designer.name,
        slug=designer.slug,
        description=designer.description,
        logo_url=designer.logo_url,
        website_url=designer.website_url,
        social_links=designer.social_links,
        membership_cost=designer.membership_cost,
        membership_start_date=designer.membership_start_date,
        membership_renewal_date=designer.membership_renewal_date,
        is_active=designer.is_active,
        notes=designer.notes,
        product_count=0,
        created_at=designer.created_at,
        updated_at=designer.updated_at,
    )


@router.patch("/{designer_id}", response_model=DesignerResponse)
async def update_designer(
    designer_id: UUID,
    designer_data: DesignerUpdate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing designer."""
    result = await db.execute(
        select(Designer).where(Designer.id == designer_id).where(Designer.tenant_id == tenant.id)
    )
    designer = result.scalar_one_or_none()

    if not designer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designer not found",
        )

    # Check slug uniqueness if being updated
    if designer_data.slug and designer_data.slug != designer.slug:
        existing = await db.execute(
            select(Designer)
            .where(Designer.tenant_id == tenant.id)
            .where(Designer.slug == designer_data.slug)
            .where(Designer.id != designer_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Designer with slug '{designer_data.slug}' already exists",
            )

    # Update fields
    update_data = designer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(designer, field, value)

    await db.commit()
    await db.refresh(designer)

    # Get product count
    count_result = await db.execute(
        select(func.count()).select_from(Product).where(Product.designer_id == designer.id)
    )
    product_count = count_result.scalar_one()

    return DesignerResponse(
        id=designer.id,
        name=designer.name,
        slug=designer.slug,
        description=designer.description,
        logo_url=designer.logo_url,
        website_url=designer.website_url,
        social_links=designer.social_links,
        membership_cost=designer.membership_cost,
        membership_start_date=designer.membership_start_date,
        membership_renewal_date=designer.membership_renewal_date,
        is_active=designer.is_active,
        notes=designer.notes,
        product_count=product_count,
        created_at=designer.created_at,
        updated_at=designer.updated_at,
    )


@router.delete("/{designer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_designer(
    designer_id: UUID,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a designer."""
    result = await db.execute(
        select(Designer).where(Designer.id == designer_id).where(Designer.tenant_id == tenant.id)
    )
    designer = result.scalar_one_or_none()

    if not designer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designer not found",
        )

    # Check if designer has products
    count_result = await db.execute(
        select(func.count()).select_from(Product).where(Product.designer_id == designer.id)
    )
    product_count = count_result.scalar_one()

    if product_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete designer with {product_count} associated products. "
            "Remove products first or set designer to inactive.",
        )

    await db.delete(designer)
    await db.commit()
