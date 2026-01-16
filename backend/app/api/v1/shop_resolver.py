"""
Multi-tenant shop resolution API endpoints.

These endpoints handle tenant discovery based on:
- Subdomain (e.g., mystmereforge.batchivo.shop)
- Path-based routing (e.g., shop.batchivo.com/mystmereforge)
- Custom domains (e.g., shop.mystmereforge.co.uk)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class ShopBrandingConfig(BaseModel):
    """Public branding configuration for shop frontend."""

    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: str = "#3B82F6"
    accent_color: str = "#10B981"
    font_family: str | None = None


class ShopLocalizationConfig(BaseModel):
    """Localization settings for shop."""

    currency: str = "GBP"
    currency_symbol: str = "£"
    locale: str = "en-GB"
    timezone: str = "Europe/London"


class ShopLabelsConfig(BaseModel):
    """Dynamic terminology labels for shop."""

    material_singular: str = "Material"
    material_plural: str = "Materials"
    design_singular: str = "Design"
    design_plural: str = "Designs"
    production_singular: str = "Item"
    production_plural: str = "Items"


class ShopFeaturesConfig(BaseModel):
    """Enabled features for shop."""

    online_shop: bool = True
    reviews: bool = True
    customer_accounts: bool = True


class ShopPublicInfo(BaseModel):
    """Public shop information."""

    name: str | None = None
    tagline: str | None = None
    about_text: str | None = None
    contact_email: str | None = None
    social_links: dict[str, str] = {}
    shipping_info: str | None = None
    return_policy: str | None = None


class TenantShopConfig(BaseModel):
    """Complete tenant shop configuration for frontend."""

    # Identification
    tenant_id: str = Field(..., description="Tenant UUID")
    slug: str = Field(..., description="URL slug")
    name: str = Field(..., description="Business name")
    tenant_type: str = Field(..., description="Tenant type")

    # Configuration sections
    branding: ShopBrandingConfig
    localization: ShopLocalizationConfig
    labels: ShopLabelsConfig
    features: ShopFeaturesConfig
    shop: ShopPublicInfo

    # Status
    is_active: bool = True


class DomainResolutionResponse(BaseModel):
    """Response from domain resolution."""

    found: bool = Field(..., description="Whether tenant was found")
    tenant_slug: str | None = Field(None, description="Resolved tenant slug")
    resolution_method: str | None = Field(
        None, description="How tenant was resolved (subdomain, custom_domain, path)"
    )
    config: TenantShopConfig | None = Field(None, description="Tenant config if found")


# =============================================================================
# Domain Resolution Logic
# =============================================================================

# Known platform domains (not tenant subdomains)
PLATFORM_DOMAINS = {
    "batchivo.com",
    "batchivo.shop",
    "www.batchivo.com",
    "www.batchivo.shop",
    "api.batchivo.com",
    "localhost",
}

# Known platform subdomains to ignore
PLATFORM_SUBDOMAINS = {"www", "api", "admin", "dashboard", "app", "shop"}


def extract_subdomain(hostname: str) -> str | None:
    """
    Extract subdomain from hostname.

    Args:
        hostname: Full hostname (e.g., mystmereforge.batchivo.shop)

    Returns:
        Subdomain or None if no valid subdomain found
    """
    # Remove port if present
    hostname = hostname.split(":")[0].lower()

    # Check if it's a platform domain (no subdomain to extract)
    if hostname in PLATFORM_DOMAINS:
        return None

    # Check for subdomain pattern (x.batchivo.shop or x.batchivo.com)
    for base_domain in ["batchivo.shop", "batchivo.com"]:
        if hostname.endswith(f".{base_domain}"):
            subdomain = hostname[: -(len(base_domain) + 1)]
            # Ignore platform subdomains
            if subdomain not in PLATFORM_SUBDOMAINS:
                return subdomain

    return None


async def resolve_tenant_by_custom_domain(db: AsyncSession, hostname: str) -> Tenant | None:
    """
    Find tenant by custom domain.

    Args:
        db: Database session
        hostname: Full hostname to check

    Returns:
        Tenant if found, None otherwise
    """
    hostname = hostname.split(":")[0].lower()

    # Query tenants where settings.shop.custom_domain matches
    # Use dialect-aware JSON extraction (works with both PostgreSQL and SQLite)
    dialect = db.bind.dialect.name if db.bind else "postgresql"

    if dialect == "sqlite":
        # SQLite uses json_extract with path syntax
        result = await db.execute(
            select(Tenant).where(
                func.json_extract(Tenant.settings, "$.shop.custom_domain") == hostname,
                Tenant.is_active.is_(True),
            )
        )
    else:
        # PostgreSQL uses jsonb_extract_path_text
        result = await db.execute(
            select(Tenant).where(
                func.jsonb_extract_path_text(Tenant.settings, "shop", "custom_domain") == hostname,
                Tenant.is_active.is_(True),
            )
        )
    return result.scalar_one_or_none()


async def resolve_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    """
    Find tenant by slug.

    Args:
        db: Database session
        slug: Tenant slug

    Returns:
        Tenant if found, None otherwise
    """
    result = await db.execute(
        select(Tenant).where(
            Tenant.slug == slug.lower(),
            Tenant.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


def build_shop_config(tenant: Tenant) -> TenantShopConfig:
    """
    Build shop configuration from tenant.

    Args:
        tenant: Tenant model

    Returns:
        Shop configuration for frontend
    """
    settings = tenant.settings or {}

    # Extract branding settings
    branding_data = settings.get("branding", {})
    branding = ShopBrandingConfig(
        logo_url=branding_data.get("logo_url"),
        favicon_url=branding_data.get("favicon_url"),
        primary_color=branding_data.get("primary_color", "#3B82F6"),
        accent_color=branding_data.get("accent_color", "#10B981"),
        font_family=branding_data.get("font_family"),
    )

    # Extract localization settings
    loc_data = settings.get("localization", {})
    localization = ShopLocalizationConfig(
        currency=loc_data.get("currency", "GBP"),
        currency_symbol=loc_data.get("currency_symbol", "£"),
        locale=loc_data.get("locale", "en-GB"),
        timezone=loc_data.get("timezone", "Europe/London"),
    )

    # Extract labels
    labels_data = settings.get("labels", {})
    labels = ShopLabelsConfig(
        material_singular=labels_data.get("material_singular", "Material"),
        material_plural=labels_data.get("material_plural", "Materials"),
        design_singular=labels_data.get("design_singular", "Design"),
        design_plural=labels_data.get("design_plural", "Designs"),
        production_singular=labels_data.get("production_singular", "Item"),
        production_plural=labels_data.get("production_plural", "Items"),
    )

    # Extract features
    features_data = settings.get("features", {})
    features = ShopFeaturesConfig(
        online_shop=features_data.get("online_shop", True),
        reviews=features_data.get("reviews", True),
        customer_accounts=features_data.get("customer_accounts", True),
    )

    # Extract shop info
    shop_data = settings.get("shop", {})
    shop = ShopPublicInfo(
        name=shop_data.get("shop_name") or tenant.name,
        tagline=shop_data.get("tagline"),
        about_text=shop_data.get("about_text"),
        contact_email=shop_data.get("contact_email"),
        social_links=shop_data.get("social_links", {}),
        shipping_info=shop_data.get("shipping_info"),
        return_policy=shop_data.get("return_policy"),
    )

    return TenantShopConfig(
        tenant_id=str(tenant.id),
        slug=tenant.slug,
        name=tenant.name,
        tenant_type=tenant.tenant_type,
        branding=branding,
        localization=localization,
        labels=labels,
        features=features,
        shop=shop,
        is_active=tenant.is_active,
    )


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "/resolve",
    response_model=DomainResolutionResponse,
    summary="Resolve tenant from hostname",
    description="Resolve tenant configuration from request hostname or custom domain.",
)
async def resolve_domain(
    hostname: str = Query(
        ..., description="Hostname to resolve (e.g., mystmereforge.batchivo.shop)"
    ),
    db: AsyncSession = Depends(get_db),
) -> DomainResolutionResponse:
    """
    Resolve tenant from hostname.

    Resolution priority:
    1. Custom domain match
    2. Subdomain extraction (x.batchivo.shop)

    Returns tenant configuration if found.
    """
    hostname = hostname.lower().strip()
    logger.info(f"Resolving tenant for hostname: {hostname}")

    # Try custom domain first
    tenant = await resolve_tenant_by_custom_domain(db, hostname)
    if tenant:
        logger.info(f"Resolved {hostname} via custom domain to {tenant.slug}")
        return DomainResolutionResponse(
            found=True,
            tenant_slug=tenant.slug,
            resolution_method="custom_domain",
            config=build_shop_config(tenant),
        )

    # Try subdomain extraction
    subdomain = extract_subdomain(hostname)
    if subdomain:
        tenant = await resolve_tenant_by_slug(db, subdomain)
        if tenant:
            logger.info(f"Resolved {hostname} via subdomain to {tenant.slug}")
            return DomainResolutionResponse(
                found=True,
                tenant_slug=tenant.slug,
                resolution_method="subdomain",
                config=build_shop_config(tenant),
            )

    # Not found
    logger.info(f"No tenant found for hostname: {hostname}")
    return DomainResolutionResponse(
        found=False,
        tenant_slug=None,
        resolution_method=None,
        config=None,
    )


@router.get(
    "/tenant/{slug}/config",
    response_model=TenantShopConfig,
    summary="Get tenant shop configuration",
    description="Get full shop configuration for a tenant by slug.",
)
async def get_tenant_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> TenantShopConfig:
    """
    Get tenant shop configuration by slug.

    This is the primary endpoint for frontend to load tenant-specific
    configuration including branding, labels, and features.
    """
    tenant = await resolve_tenant_by_slug(db, slug)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shop '{slug}' not found",
        )

    # Check if shop is enabled
    settings = tenant.settings or {}
    shop_settings = settings.get("shop", {})
    if not shop_settings.get("enabled", False):
        # Shop not enabled, but we still return config for preview
        logger.warning(f"Shop {slug} is not enabled, returning config for preview")

    return build_shop_config(tenant)


@router.get(
    "/tenant/{slug}/exists",
    summary="Check if tenant exists",
    description="Quick check if a tenant slug exists and is active.",
)
async def check_tenant_exists(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Check if tenant exists by slug.

    Quick validation endpoint for frontend routing.
    """
    tenant = await resolve_tenant_by_slug(db, slug)

    if tenant:
        return {
            "exists": True,
            "slug": tenant.slug,
            "name": tenant.name,
            "is_active": tenant.is_active,
        }

    return {
        "exists": False,
        "slug": slug,
        "name": None,
        "is_active": False,
    }
