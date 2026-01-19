"""User API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Get current user information.

    Returns the authenticated user's profile data including
    their tenant information.
    """
    # Get user's primary tenant
    from sqlalchemy import select
    from app.models.user import UserTenant
    from app.models.tenant import Tenant

    result = await db.execute(
        select(UserTenant)
        .where(UserTenant.user_id == current_user.id)
        .order_by(UserTenant.created_at.asc())
        .limit(1)
    )
    user_tenant = result.scalar_one_or_none()

    if user_tenant:
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == user_tenant.tenant_id))
        tenant = tenant_result.scalar_one_or_none()

        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            name=current_user.full_name or current_user.email.split("@")[0],
            tenant_id=str(tenant.id) if tenant else None,
            tenant_name=tenant.name if tenant else None,
            currency_code=tenant.currency_code if tenant else "GBP",
            currency_symbol=tenant.currency_symbol if tenant else "£",
            is_platform_admin=current_user.is_platform_admin,
        )

    # User has no tenant (shouldn't happen but handle gracefully)
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.full_name or current_user.email.split("@")[0],
        tenant_id=None,
        tenant_name=None,
        currency_code="GBP",
        currency_symbol="£",
        is_platform_admin=current_user.is_platform_admin,
    )
