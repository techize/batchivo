"""Authentication dependencies for FastAPI routes."""

import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session_maker, get_db
from app.models.tenant import Tenant
from app.models.user import User, UserTenant

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[Optional[str], Header()] = None,
) -> User:
    """
    Get the current authenticated user from JWT token.

    Validates JWT access token and returns the user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "")

    # Decode JWT token using our security module
    from app.core.security import decode_token, verify_token_type

    # Verify it's an access token
    if not verify_token_type(token, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode token
    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Look up user
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_tenant(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_tenant_id: Annotated[Optional[str], Header()] = None,
) -> Tenant:
    """
    Get the current tenant for the authenticated user.

    Selection Priority:
    1. X-Tenant-ID header (if provided and user has access)
    2. User's first tenant (default)

    In production, this might also check subdomain or path.
    """
    # Get user's tenants
    result = await db.execute(
        select(UserTenant)
        .where(UserTenant.user_id == user.id)
        .order_by(UserTenant.created_at.asc())
    )
    user_tenants = result.scalars().all()

    if not user_tenants:
        # User has no tenants - auto-create a default one
        # Note: In a mature SaaS, you might require explicit tenant creation/invitation
        # For now, auto-create to simplify onboarding
        tenant = Tenant(
            name=f"{user.full_name}'s Workspace",
            slug=f"user-{user.id}",
            is_active=True,
            settings={},
        )
        db.add(tenant)
        await db.flush()  # Flush to get tenant.id before using it

        # Create owner relationship
        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=tenant.id,
            role="owner",
        )
        db.add(user_tenant)

        await db.commit()
        await db.refresh(tenant)
        return tenant

    # If tenant ID specified in header, verify access
    if x_tenant_id:
        try:
            tenant_uuid = uuid.UUID(x_tenant_id)
            for ut in user_tenants:
                if ut.tenant_id == tenant_uuid:
                    result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
                    return result.scalar_one()
        except (ValueError, Exception):
            pass

    # Return user's first tenant (default)
    result = await db.execute(select(Tenant).where(Tenant.id == user_tenants[0].tenant_id))
    return result.scalar_one()


async def require_role(
    user: Annotated[User, Depends(get_current_user)],
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
    required_role: str = "member",
) -> bool:
    """
    Check if user has required role in current tenant.

    Role hierarchy: owner > admin > member > viewer

    Returns True if authorized, raises HTTPException if not.
    """
    # Get user's role in this tenant
    result = await db.execute(
        select(UserTenant).where(UserTenant.user_id == user.id, UserTenant.tenant_id == tenant.id)
    )
    user_tenant = result.scalar_one_or_none()

    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this tenant",
        )

    # Role hierarchy check
    role_hierarchy = {
        "viewer": 0,
        "member": 1,
        "admin": 2,
        "owner": 3,
    }

    user_level = role_hierarchy.get(user_tenant.role, 0)
    required_level = role_hierarchy.get(required_role, 0)

    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {required_role} role or higher",
        )

    return True


def require_admin():
    """Dependency that requires admin role or higher."""

    async def check_admin(
        user: Annotated[User, Depends(get_current_user)],
        tenant: Annotated[Tenant, Depends(get_current_tenant)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> bool:
        return await require_role(user, tenant, db, "admin")

    return check_admin


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
RequireAdmin = Annotated[bool, Depends(require_admin())]


async def get_platform_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Require platform admin access.

    This dependency validates that the current user has platform-wide
    admin privileges. Use for endpoints that manage tenants, users
    across tenants, or platform settings.

    Raises:
        HTTPException: 403 if user is not a platform admin
    """
    if not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return user


# Type alias for platform admin dependency
PlatformAdmin = Annotated[User, Depends(get_platform_admin)]


async def get_tenant_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with RLS tenant context set.

    This dependency should be used instead of get_db for routes that need
    tenant isolation via Row-Level Security. It:
    1. Gets tenant_id from request.state (set by TenantContextMiddleware)
    2. Creates a new database session
    3. Sets the PostgreSQL session variable app.current_tenant_id
    4. Yields the session for use by the route handler

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_tenant_db)):
            # All queries automatically filtered by tenant_id
            result = await db.execute(select(Item))
            return result.scalars().all()

    Note: If RLS is disabled (settings.rls_enabled=False) or tenant_id is not
    available, the session is returned without setting the variable. This
    allows gradual migration and public endpoints to work.
    """
    async with async_session_maker() as session:
        try:
            # Get tenant_id from request state (set by TenantContextMiddleware)
            tenant_id = getattr(request.state, "tenant_id", None)

            # Set RLS context if enabled and tenant_id is available
            if settings.rls_enabled and tenant_id:
                # SET LOCAL ensures the variable is transaction-scoped
                # It automatically clears when the transaction ends
                await session.execute(
                    text("SET LOCAL app.current_tenant_id = :tenant_id"),
                    {"tenant_id": str(tenant_id)},
                )
                logger.debug(f"RLS context set: tenant_id={tenant_id}")

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for RLS-enabled database session
TenantDB = Annotated[AsyncSession, Depends(get_tenant_db)]


async def get_platform_admin_db(
    _admin: Annotated[User, Depends(get_platform_admin)],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session for platform admin WITHOUT RLS tenant scoping.

    This dependency:
    1. Validates the user is a platform admin (via get_platform_admin)
    2. Returns a database session WITHOUT setting app.current_tenant_id
    3. Allows cross-tenant queries for platform-wide operations

    Use for endpoints that need to query across all tenants, such as:
    - Listing all tenants
    - Searching users across tenants
    - Platform-wide analytics

    Note: The _admin parameter ensures platform admin access is validated
    before granting cross-tenant database access.
    """
    async with async_session_maker() as session:
        try:
            # DO NOT set app.current_tenant_id - bypass RLS
            # This allows cross-tenant queries for platform admins
            logger.debug("Platform admin DB session created (RLS bypassed)")
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for platform admin database session (bypasses RLS)
PlatformAdminDB = Annotated[AsyncSession, Depends(get_platform_admin_db)]


async def get_shop_tenant(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_shop_hostname: Annotated[str, Header(description="Shop hostname for tenant resolution")],
) -> Tenant:
    """
    Resolve tenant from shop hostname (subdomain or custom domain).

    This dependency is used for PUBLIC shop endpoints that need tenant context
    without requiring user authentication.

    Resolution priority:
    1. Custom domain match (e.g., shop.mystmereforge.co.uk)
    2. Subdomain extraction (e.g., mystmereforge.batchivo.shop)

    The shop frontend passes the hostname in the X-Shop-Hostname header.

    Raises:
        HTTPException: 404 if no tenant found for hostname
    """
    from app.api.v1.shop_resolver import (
        extract_subdomain,
        resolve_tenant_by_custom_domain,
        resolve_tenant_by_slug,
    )

    hostname = x_shop_hostname.lower().strip()
    logger.debug(f"Resolving shop tenant for hostname: {hostname}")

    # Try custom domain first
    tenant = await resolve_tenant_by_custom_domain(db, hostname)
    if tenant:
        logger.info(f"Resolved shop tenant via custom domain: {tenant.slug}")
        return tenant

    # Try subdomain extraction
    subdomain = extract_subdomain(hostname)
    if subdomain:
        tenant = await resolve_tenant_by_slug(db, subdomain)
        if tenant:
            logger.info(f"Resolved shop tenant via subdomain: {tenant.slug}")
            return tenant

    # No tenant found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Shop not found for hostname: {hostname}",
    )


# Type alias for shop tenant dependency (public, no auth required)
ShopTenant = Annotated[Tenant, Depends(get_shop_tenant)]


async def get_shop_sales_channel(
    db: Annotated[AsyncSession, Depends(get_db)],
    shop_tenant: Annotated[Tenant, Depends(get_shop_tenant)],
):
    """
    Get the shop sales channel for the resolved tenant.

    This dependency resolves the tenant's "online_shop" sales channel
    which is used for pricing lookups in public shop endpoints.

    Returns:
        Tuple of (Tenant, SalesChannel) for the shop

    Raises:
        HTTPException: 500 if tenant has no online shop channel configured
    """
    from app.models.sales_channel import SalesChannel

    # Find the tenant's online shop sales channel
    result = await db.execute(
        select(SalesChannel).where(
            SalesChannel.tenant_id == shop_tenant.id,
            SalesChannel.platform_type == "online_shop",
            SalesChannel.is_active.is_(True),
        )
    )
    channel = result.scalar_one_or_none()

    if not channel:
        logger.error(f"Tenant {shop_tenant.slug} has no online_shop sales channel")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Shop '{shop_tenant.slug}' is not properly configured (no sales channel)",
        )

    return shop_tenant, channel


# Type alias for shop context (tenant + sales channel)
ShopContext = Annotated[tuple[Tenant, "SalesChannel"], Depends(get_shop_sales_channel)]
