"""Settings API endpoints for tenant configuration."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser
from app.database import get_db
from app.models.user import UserRole
from app.schemas.tenant_settings import (
    BrandingSettingsResponse,
    BrandingSettingsUpdate,
    CustomDomainInitResponse,
    CustomDomainRequest,
    CustomDomainStatusResponse,
    CustomDomainVerifyResponse,
    ShopSettingsResponse,
    ShopSettingsUpdate,
    SquareConnectionTest,
    SquareSettingsResponse,
    SquareSettingsUpdate,
    TenantResponse,
    TenantUpdate,
)
from app.services.domain_verification import DomainVerificationService
from app.services.tenant_settings import TenantSettingsService

router = APIRouter()


def _require_admin_role(user: CurrentUser, tenant: CurrentTenant) -> None:
    """Check that user has admin or owner role for settings access.

    Args:
        user: The current user
        tenant: The current tenant

    Raises:
        HTTPException: If user doesn't have sufficient permissions
    """
    # Find user's role in this tenant
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
            detail="Admin or Owner role required to modify settings",
        )


# =============================================================================
# Square Payment Settings
# =============================================================================


@router.get("/square", response_model=SquareSettingsResponse)
async def get_square_settings(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SquareSettingsResponse:
    """Get Square payment gateway settings.

    Returns the current Square configuration with masked credentials.
    Only shows last 4 characters of sensitive values.
    """
    service = TenantSettingsService(db)
    return await service.get_square_settings(tenant.id)


@router.put("/square", response_model=SquareSettingsResponse)
async def update_square_settings(
    data: SquareSettingsUpdate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SquareSettingsResponse:
    """Update Square payment gateway settings.

    Requires Admin or Owner role.
    Credentials are encrypted before storage.
    """
    _require_admin_role(user, tenant)

    service = TenantSettingsService(db)
    return await service.update_square_settings(tenant.id, data)


@router.post("/square/test", response_model=SquareConnectionTest)
async def test_square_connection(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SquareConnectionTest:
    """Test Square connection with current credentials.

    Attempts to connect to Square API and retrieve location details.
    Returns success status and any error messages.
    """
    _require_admin_role(user, tenant)

    service = TenantSettingsService(db)
    return await service.test_square_connection(tenant.id)


# =============================================================================
# Tenant Settings
# =============================================================================


@router.get("/tenant", response_model=TenantResponse)
async def get_tenant_settings(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Get tenant details.

    Returns the tenant's name, description, and other metadata.
    """
    service = TenantSettingsService(db)
    return await service.get_tenant(tenant.id)


@router.put("/tenant", response_model=TenantResponse)
async def update_tenant_settings(
    data: TenantUpdate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Update tenant details.

    Requires Admin or Owner role.
    Can update tenant name and description.
    """
    _require_admin_role(user, tenant)

    service = TenantSettingsService(db)
    return await service.update_tenant(tenant.id, data)


# =============================================================================
# Shop Settings
# =============================================================================


@router.get("/shop", response_model=ShopSettingsResponse)
async def get_shop_settings(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ShopSettingsResponse:
    """Get shop configuration settings.

    Returns the tenant's shop configuration including:
    - Shop name and tagline
    - Custom domain settings
    - Order prefix
    - Contact information
    - Social media links
    - Checkout options
    """
    service = TenantSettingsService(db)
    return await service.get_shop_settings(tenant.id)


@router.put("/shop", response_model=ShopSettingsResponse)
async def update_shop_settings(
    data: ShopSettingsUpdate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ShopSettingsResponse:
    """Update shop configuration settings.

    Requires Admin or Owner role.
    Allows partial updates - only provided fields are updated.

    Note: custom_domain_verified is read-only and cannot be set directly.
    Use the custom domain verification endpoints instead.
    """
    _require_admin_role(user, tenant)

    service = TenantSettingsService(db)
    return await service.update_shop_settings(tenant.id, data)


# =============================================================================
# Branding Settings
# =============================================================================


@router.get("/branding", response_model=BrandingSettingsResponse)
async def get_branding_settings(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BrandingSettingsResponse:
    """Get branding configuration settings.

    Returns the tenant's branding configuration including:
    - Logo and favicon URLs
    - Primary and accent colors (hex format)
    - Custom font family
    """
    service = TenantSettingsService(db)
    return await service.get_branding_settings(tenant.id)


@router.put("/branding", response_model=BrandingSettingsResponse)
async def update_branding_settings(
    data: BrandingSettingsUpdate,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BrandingSettingsResponse:
    """Update branding configuration settings.

    Requires Admin or Owner role.
    Allows partial updates - only provided fields are updated.

    Colors must be valid 6-digit hex codes (e.g., #3B82F6).
    """
    _require_admin_role(user, tenant)

    service = TenantSettingsService(db)
    return await service.update_branding_settings(tenant.id, data)


# =============================================================================
# Custom Domain Settings
# =============================================================================


@router.post("/custom-domain", response_model=CustomDomainInitResponse)
async def initialize_custom_domain(
    data: CustomDomainRequest,
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CustomDomainInitResponse:
    """Initialize custom domain setup.

    Requires Admin or Owner role.

    Generates a verification token and returns DNS setup instructions.
    The domain must be verified before it becomes active.

    Steps:
    1. Add a CNAME record pointing to shops.nozzly.app
    2. Add a TXT record with the verification token
    3. Call POST /custom-domain/verify to complete verification
    """
    _require_admin_role(user, tenant)

    service = DomainVerificationService(db)
    result = await service.initiate_domain_verification(tenant.id, data.domain)

    return CustomDomainInitResponse(
        domain=result["domain"],
        verification_token=result["verification_token"],
        cname_target=result["cname_target"],
        txt_record_host=result["txt_record_host"],
        instructions=result["instructions"],
    )


@router.get("/custom-domain/status", response_model=CustomDomainStatusResponse)
async def get_custom_domain_status(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CustomDomainStatusResponse:
    """Get current custom domain verification status.

    Returns the domain configuration and verification state.
    """
    service = DomainVerificationService(db)
    result = await service.get_verification_status(tenant.id)

    return CustomDomainStatusResponse(**result)


@router.post("/custom-domain/verify", response_model=CustomDomainVerifyResponse)
async def verify_custom_domain(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CustomDomainVerifyResponse:
    """Trigger DNS verification for the custom domain.

    Requires Admin or Owner role.

    Checks both CNAME and TXT records. If both are correctly configured,
    the domain is marked as verified and becomes active.

    Note: DNS changes can take up to 48 hours to propagate.
    """
    _require_admin_role(user, tenant)

    service = DomainVerificationService(db)
    result = await service.complete_domain_verification(tenant.id)

    return CustomDomainVerifyResponse(**result)


@router.delete("/custom-domain")
async def remove_custom_domain(
    tenant: CurrentTenant,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove custom domain configuration.

    Requires Admin or Owner role.

    Removes the custom domain and resets verification status.
    The shop will revert to using the subdomain (slug.nozzly.shop).
    """
    _require_admin_role(user, tenant)

    service = DomainVerificationService(db)
    result = await service.remove_custom_domain(tenant.id)

    return result
