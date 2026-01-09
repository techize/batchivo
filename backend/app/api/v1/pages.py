"""Content page management API endpoints (policies, info pages)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.page import Page, PageType
from app.schemas.page import (
    PageCreate,
    PageListResponse,
    PageResponse,
    PageUpdate,
    slugify,
)

router = APIRouter()


@router.get("", response_model=PageListResponse)
async def list_pages(
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    include_unpublished: bool = Query(True, description="Include unpublished pages"),
    page_type: Optional[PageType] = Query(None, description="Filter by page type"),
    search: Optional[str] = Query(None, description="Search by title"),
):
    """List all content pages for the tenant."""
    query = select(Page).where(Page.tenant_id == tenant.id)

    if not include_unpublished:
        query = query.where(Page.is_published.is_(True))

    if page_type:
        query = query.where(Page.page_type == page_type.value)

    if search:
        query = query.where(Page.title.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # Apply pagination and ordering
    query = query.order_by(Page.sort_order, Page.title).offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    pages = result.scalars().all()

    return PageListResponse(
        pages=[PageResponse.model_validate(p) for p in pages],
        total=total,
    )


@router.get("/{page_id}", response_model=PageResponse)
async def get_page(
    page_id: UUID,
    tenant: CurrentTenant,
    db: AsyncSession = Depends(get_db),
):
    """Get a single page by ID."""
    result = await db.execute(
        select(Page).where(Page.id == page_id).where(Page.tenant_id == tenant.id)
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    return PageResponse.model_validate(page)


@router.post("", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    page_data: PageCreate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new content page."""
    # Generate slug from title if not provided
    slug = page_data.slug if page_data.slug else slugify(page_data.title)

    # Check slug uniqueness within tenant
    existing = await db.execute(
        select(Page).where(Page.tenant_id == tenant.id).where(Page.slug == slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Page with slug '{slug}' already exists",
        )

    page = Page(
        tenant_id=tenant.id,
        slug=slug,
        title=page_data.title,
        content=page_data.content,
        page_type=page_data.page_type.value,
        meta_description=page_data.meta_description,
        is_published=page_data.is_published,
        sort_order=page_data.sort_order,
    )

    db.add(page)
    await db.commit()
    await db.refresh(page)

    return PageResponse.model_validate(page)


@router.patch("/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: UUID,
    page_data: PageUpdate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update a content page."""
    result = await db.execute(
        select(Page).where(Page.id == page_id).where(Page.tenant_id == tenant.id)
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    # Check slug uniqueness if being updated
    if page_data.slug and page_data.slug != page.slug:
        existing = await db.execute(
            select(Page)
            .where(Page.tenant_id == tenant.id)
            .where(Page.slug == page_data.slug)
            .where(Page.id != page_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Page with slug '{page_data.slug}' already exists",
            )

    # Update fields
    update_data = page_data.model_dump(exclude_unset=True)

    # Handle page_type enum conversion
    if "page_type" in update_data and update_data["page_type"]:
        update_data["page_type"] = update_data["page_type"].value

    for field, value in update_data.items():
        setattr(page, field, value)

    await db.commit()
    await db.refresh(page)

    return PageResponse.model_validate(page)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_page(
    page_id: UUID,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    hard_delete: bool = Query(False, description="Permanently delete (default: unpublish)"),
):
    """Delete a page (unpublish by default, hard delete if specified)."""
    result = await db.execute(
        select(Page).where(Page.id == page_id).where(Page.tenant_id == tenant.id)
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Page not found",
        )

    if hard_delete:
        await db.delete(page)
    else:
        page.is_published = False

    await db.commit()
    return None
