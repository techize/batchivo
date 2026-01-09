"""Tenant member management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.user import User, UserRole, UserTenant
from app.schemas.tenant_settings import (
    TenantMemberInvite,
    TenantMemberListResponse,
    TenantMemberResponse,
    TenantMemberRoleUpdate,
)

router = APIRouter()


def _require_admin_role(user: CurrentUser, tenant: CurrentTenant) -> None:
    """Check that user has admin or owner role.

    Args:
        user: The current user
        tenant: The current tenant

    Raises:
        HTTPException: If user doesn't have sufficient permissions
    """
    user_tenant = next(
        (ut for ut in user.user_tenants if ut.tenant_id == tenant.id),
        None,
    )

    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this tenant",
        )

    if user_tenant.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Owner role required",
        )


def _get_current_user_role(user: CurrentUser, tenant: CurrentTenant) -> UserRole:
    """Get the current user's role in the tenant."""
    user_tenant = next(
        (ut for ut in user.user_tenants if ut.tenant_id == tenant.id),
        None,
    )
    return user_tenant.role if user_tenant else None


@router.get("", response_model=TenantMemberListResponse)
async def list_members(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TenantMemberListResponse:
    """List all members of the current tenant.

    Returns all users who are members of the tenant with their roles.
    """
    # Query members with user details
    stmt = (
        select(UserTenant)
        .where(UserTenant.tenant_id == tenant.id)
        .options(selectinload(UserTenant.user))
    )
    result = await db.execute(stmt)
    user_tenants = result.scalars().all()

    members = [
        TenantMemberResponse(
            id=ut.user.id,
            email=ut.user.email,
            full_name=ut.user.full_name,
            role=ut.role,
            is_active=ut.user.is_active,
            joined_at=ut.created_at,
        )
        for ut in user_tenants
    ]

    return TenantMemberListResponse(members=members, total=len(members))


@router.post("/invite", response_model=TenantMemberResponse)
async def invite_member(
    data: TenantMemberInvite,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TenantMemberResponse:
    """Invite a user to the tenant.

    If the user exists, adds them to the tenant.
    If not, creates a placeholder (they'll need to register).

    Requires Admin or Owner role.
    """
    _require_admin_role(user, tenant)

    # Check if inviter is trying to assign a higher role
    current_role = _get_current_user_role(user, tenant)
    if data.role == UserRole.OWNER and current_role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can assign the owner role",
        )

    # Find existing user by email
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Check if already a member
        member_stmt = select(UserTenant).where(
            UserTenant.user_id == existing_user.id,
            UserTenant.tenant_id == tenant.id,
        )
        member_result = await db.execute(member_stmt)
        existing_membership = member_result.scalar_one_or_none()

        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this tenant",
            )

        # Add user to tenant
        new_membership = UserTenant(
            user_id=existing_user.id,
            tenant_id=tenant.id,
            role=data.role,
        )
        db.add(new_membership)
        await db.commit()
        await db.refresh(new_membership)

        return TenantMemberResponse(
            id=existing_user.id,
            email=existing_user.email,
            full_name=existing_user.full_name,
            role=data.role,
            is_active=existing_user.is_active,
            joined_at=new_membership.created_at,
        )
    else:
        # User doesn't exist - for now, return an error
        # In a full implementation, you'd send an invitation email
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user found with email {data.email}. They need to register first.",
        )


@router.put("/{member_id}", response_model=TenantMemberResponse)
async def update_member_role(
    member_id: UUID,
    data: TenantMemberRoleUpdate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TenantMemberResponse:
    """Update a member's role in the tenant.

    Requires Admin or Owner role.
    Only owners can promote to owner or demote other owners.
    """
    _require_admin_role(user, tenant)
    current_role = _get_current_user_role(user, tenant)

    # Find the membership
    stmt = (
        select(UserTenant)
        .where(
            UserTenant.user_id == member_id,
            UserTenant.tenant_id == tenant.id,
        )
        .options(selectinload(UserTenant.user))
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this tenant",
        )

    # Prevent self-demotion for owners
    if membership.user_id == user.id and membership.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owners cannot demote themselves",
        )

    # Only owners can assign/remove owner role
    if data.role == UserRole.OWNER and current_role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can assign the owner role",
        )

    if membership.role == UserRole.OWNER and current_role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can modify other owners",
        )

    # Update role
    membership.role = data.role
    await db.commit()
    await db.refresh(membership)

    return TenantMemberResponse(
        id=membership.user.id,
        email=membership.user.email,
        full_name=membership.user.full_name,
        role=membership.role,
        is_active=membership.user.is_active,
        joined_at=membership.created_at,
    )


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: UUID,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a member from the tenant.

    Requires Admin or Owner role.
    Owners cannot be removed (must transfer ownership first).
    Users cannot remove themselves.
    """
    _require_admin_role(user, tenant)
    current_role = _get_current_user_role(user, tenant)

    # Find the membership
    stmt = select(UserTenant).where(
        UserTenant.user_id == member_id,
        UserTenant.tenant_id == tenant.id,
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this tenant",
        )

    # Prevent self-removal
    if membership.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself from the tenant",
        )

    # Prevent removing owners (unless current user is also owner)
    if membership.role == UserRole.OWNER and current_role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can remove other owners",
        )

    # Delete membership
    await db.delete(membership)
    await db.commit()
