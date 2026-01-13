"""Pydantic schemas for tenant settings and management."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Re-export UserRole from models for API use
class UserRole(str, Enum):
    """User roles within a tenant."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# =============================================================================
# Tenant Type Enum (mirrors model enum for API use)
# =============================================================================


class TenantType(str, Enum):
    """Tenant business type determining features and terminology."""

    THREE_D_PRINT = "three_d_print"
    HAND_KNITTING = "hand_knitting"
    MACHINE_KNITTING = "machine_knitting"
    GENERIC = "generic"


# =============================================================================
# Branding Settings
# =============================================================================


class BrandingSettings(BaseModel):
    """Tenant branding configuration."""

    model_config = ConfigDict(extra="ignore")

    logo_url: str | None = Field(None, description="URL to tenant logo")
    favicon_url: str | None = Field(None, description="URL to favicon")
    primary_color: str = Field(default="#3B82F6", description="Primary brand color (hex)")
    accent_color: str = Field(default="#10B981", description="Accent/secondary color (hex)")
    font_family: str | None = Field(None, description="Custom font family")


# =============================================================================
# Localization Settings
# =============================================================================


class LocalizationSettings(BaseModel):
    """Tenant localization and regional settings."""

    model_config = ConfigDict(extra="ignore")

    currency: str = Field(default="GBP", description="ISO 4217 currency code")
    currency_symbol: str = Field(default="£", description="Currency display symbol")
    timezone: str = Field(default="Europe/London", description="IANA timezone")
    locale: str = Field(default="en-GB", description="BCP 47 locale code")
    date_format: str = Field(default="DD/MM/YYYY", description="Date display format")
    weight_unit: Literal["g", "kg", "oz", "lb"] = Field(
        default="g", description="Default weight unit"
    )
    length_unit: Literal["mm", "cm", "m", "in", "ft"] = Field(
        default="mm", description="Default length unit"
    )


# =============================================================================
# Dynamic Labels (craft-specific terminology)
# =============================================================================


class DynamicLabels(BaseModel):
    """
    Customizable terminology for different craft types.

    Allows tenants to use domain-specific language:
    - 3D Printing: spool, filament, printer, model
    - Knitting: skein/ball, yarn, needles, pattern
    """

    model_config = ConfigDict(extra="ignore")

    # Material terminology
    material_singular: str = Field(default="Spool", description="Singular material term")
    material_plural: str = Field(default="Spools", description="Plural material term")
    material_type_singular: str = Field(default="Material", description="Material type singular")
    material_type_plural: str = Field(default="Materials", description="Material type plural")

    # Equipment terminology
    equipment_singular: str = Field(default="Printer", description="Equipment singular")
    equipment_plural: str = Field(default="Printers", description="Equipment plural")

    # Production terminology
    production_singular: str = Field(default="Print", description="Production singular")
    production_plural: str = Field(default="Prints", description="Production plural")
    production_run_singular: str = Field(
        default="Production Run", description="Production run singular"
    )
    production_run_plural: str = Field(
        default="Production Runs", description="Production run plural"
    )

    # Design/pattern terminology
    design_singular: str = Field(default="Model", description="Design singular")
    design_plural: str = Field(default="Models", description="Design plural")


# =============================================================================
# Feature Flags
# =============================================================================


class TenantFeatures(BaseModel):
    """
    Feature flags controlling which modules are enabled for a tenant.

    Different tenant types have different default features:
    - 3D Printing: spool tracking, production runs, printer management
    - Knitting: yarn tracking, needle inventory, pattern library, project tracking
    """

    model_config = ConfigDict(extra="ignore")

    # Core inventory features
    inventory_tracking: bool = Field(default=True, description="Enable inventory management")
    consumption_tracking: bool = Field(default=True, description="Track material consumption")
    low_stock_alerts: bool = Field(default=True, description="Enable low stock alerts")

    # Production features
    production_runs: bool = Field(default=True, description="Enable production run tracking")
    time_tracking: bool = Field(default=False, description="Enable manual time tracking")
    cost_calculation: bool = Field(default=True, description="Enable cost/pricing calculations")

    # Equipment features
    equipment_management: bool = Field(
        default=True, description="Enable equipment/printer management"
    )
    equipment_connections: bool = Field(
        default=False, description="Enable IoT equipment connections (Bambu, etc.)"
    )

    # Shop features
    online_shop: bool = Field(default=True, description="Enable e-commerce shop")
    customer_accounts: bool = Field(default=True, description="Enable customer accounts")
    order_management: bool = Field(default=True, description="Enable order management")
    reviews: bool = Field(default=True, description="Enable product reviews")

    # Craft-specific features (knitting)
    pattern_library: bool = Field(default=False, description="Enable pattern/design library")
    project_tracking: bool = Field(
        default=False, description="Enable project tracking (WIP, completed)"
    )
    needle_inventory: bool = Field(default=False, description="Enable needle/tool inventory")
    gauge_tracking: bool = Field(default=False, description="Enable gauge swatch tracking")

    # Analytics
    analytics_dashboard: bool = Field(default=True, description="Enable analytics dashboard")
    export_data: bool = Field(default=True, description="Enable data export")


# =============================================================================
# Shop Settings
# =============================================================================


class ShopSettings(BaseModel):
    """E-commerce shop configuration."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=False, description="Shop is publicly accessible")
    shop_name: str | None = Field(None, description="Public shop name")
    shop_url_slug: str | None = Field(None, description="URL slug for shop (e.g., mystmereforge)")
    custom_domain: str | None = Field(
        None, description="Custom domain (e.g., shop.mystmereforge.co.uk)"
    )
    custom_domain_verified: bool = Field(
        default=False, description="Whether custom domain DNS is verified"
    )
    order_prefix: str | None = Field(
        None, description="Order number prefix (e.g., MF for MF-20251231-001)"
    )
    tagline: str | None = Field(None, description="Shop tagline/slogan")
    about_text: str | None = Field(None, description="About the shop/business")
    contact_email: str | None = Field(None, description="Public contact email")
    social_links: dict[str, str] = Field(default_factory=dict, description="Social media links")
    shipping_info: str | None = Field(None, description="Shipping information text")
    return_policy: str | None = Field(None, description="Return policy text")


# =============================================================================
# Complete Tenant Settings
# =============================================================================


class TenantSettings(BaseModel):
    """
    Complete tenant settings structure stored in tenant.settings JSONB.

    This is the canonical schema for tenant configuration, validated
    on read/write from the database.
    """

    model_config = ConfigDict(extra="ignore")

    # Core configuration
    tenant_type: TenantType = Field(
        default=TenantType.THREE_D_PRINT, description="Tenant business type"
    )

    # Sub-configurations
    branding: BrandingSettings = Field(default_factory=BrandingSettings)
    localization: LocalizationSettings = Field(default_factory=LocalizationSettings)
    labels: DynamicLabels = Field(default_factory=DynamicLabels)
    features: TenantFeatures = Field(default_factory=TenantFeatures)
    shop: ShopSettings = Field(default_factory=ShopSettings)

    # Legacy fields (for backward compatibility)
    default_labor_rate: float = Field(default=20.0, description="Default hourly labor rate")
    currency: str = Field(default="GBP", description="Legacy currency field")

    @classmethod
    def for_tenant_type(cls, tenant_type: TenantType) -> "TenantSettings":
        """
        Factory method to create default settings for a specific tenant type.

        Args:
            tenant_type: The type of tenant to create settings for

        Returns:
            TenantSettings configured with appropriate defaults
        """
        if tenant_type == TenantType.THREE_D_PRINT:
            return cls._three_d_print_defaults()
        elif tenant_type == TenantType.HAND_KNITTING:
            return cls._hand_knitting_defaults()
        elif tenant_type == TenantType.MACHINE_KNITTING:
            return cls._machine_knitting_defaults()
        else:
            return cls._generic_defaults()

    @classmethod
    def _three_d_print_defaults(cls) -> "TenantSettings":
        """Default settings for 3D printing tenants."""
        return cls(
            tenant_type=TenantType.THREE_D_PRINT,
            labels=DynamicLabels(
                material_singular="Spool",
                material_plural="Spools",
                material_type_singular="Filament",
                material_type_plural="Filaments",
                equipment_singular="Printer",
                equipment_plural="Printers",
                production_singular="Print",
                production_plural="Prints",
                production_run_singular="Production Run",
                production_run_plural="Production Runs",
                design_singular="Model",
                design_plural="Models",
            ),
            features=TenantFeatures(
                inventory_tracking=True,
                consumption_tracking=True,
                production_runs=True,
                equipment_management=True,
                equipment_connections=True,  # Bambu Lab integration
                online_shop=True,
                pattern_library=False,
                project_tracking=False,
                needle_inventory=False,
                gauge_tracking=False,
            ),
        )

    @classmethod
    def _hand_knitting_defaults(cls) -> "TenantSettings":
        """Default settings for hand knitting tenants."""
        return cls(
            tenant_type=TenantType.HAND_KNITTING,
            labels=DynamicLabels(
                material_singular="Skein",
                material_plural="Skeins",
                material_type_singular="Yarn",
                material_type_plural="Yarns",
                equipment_singular="Needle Set",
                equipment_plural="Needle Sets",
                production_singular="Project",
                production_plural="Projects",
                production_run_singular="Project",
                production_run_plural="Projects",
                design_singular="Pattern",
                design_plural="Patterns",
            ),
            features=TenantFeatures(
                inventory_tracking=True,
                consumption_tracking=True,
                production_runs=False,  # Use project tracking instead
                time_tracking=True,  # Time spent on projects
                equipment_management=True,  # Needles, hooks, etc.
                equipment_connections=False,  # No IoT for hand knitting
                online_shop=True,
                pattern_library=True,
                project_tracking=True,
                needle_inventory=True,
                gauge_tracking=True,
            ),
        )

    @classmethod
    def _machine_knitting_defaults(cls) -> "TenantSettings":
        """Default settings for machine knitting tenants."""
        return cls(
            tenant_type=TenantType.MACHINE_KNITTING,
            labels=DynamicLabels(
                material_singular="Cone",
                material_plural="Cones",
                material_type_singular="Yarn",
                material_type_plural="Yarns",
                equipment_singular="Machine",
                equipment_plural="Machines",
                production_singular="Piece",
                production_plural="Pieces",
                production_run_singular="Production Run",
                production_run_plural="Production Runs",
                design_singular="Pattern",
                design_plural="Patterns",
            ),
            features=TenantFeatures(
                inventory_tracking=True,
                consumption_tracking=True,
                production_runs=True,
                time_tracking=True,
                equipment_management=True,
                equipment_connections=False,  # Future: machine connectivity
                online_shop=True,
                pattern_library=True,
                project_tracking=True,
                needle_inventory=False,  # Machines have built-in needles
                gauge_tracking=True,
            ),
        )

    @classmethod
    def _generic_defaults(cls) -> "TenantSettings":
        """Default settings for generic maker tenants."""
        return cls(
            tenant_type=TenantType.GENERIC,
            labels=DynamicLabels(
                material_singular="Material",
                material_plural="Materials",
                material_type_singular="Material Type",
                material_type_plural="Material Types",
                equipment_singular="Equipment",
                equipment_plural="Equipment",
                production_singular="Item",
                production_plural="Items",
                production_run_singular="Production Run",
                production_run_plural="Production Runs",
                design_singular="Design",
                design_plural="Designs",
            ),
            features=TenantFeatures(
                inventory_tracking=True,
                consumption_tracking=True,
                production_runs=True,
                time_tracking=True,
                equipment_management=True,
                equipment_connections=False,
                online_shop=True,
                pattern_library=True,
                project_tracking=True,
                needle_inventory=False,
                gauge_tracking=False,
            ),
        )


# =============================================================================
# Etsy Settings Schemas
# =============================================================================


class EtsySettingsUpdate(BaseModel):
    """Schema for updating Etsy marketplace settings."""

    enabled: bool | None = Field(None, description="Enable/disable Etsy integration")
    api_key: str | None = Field(None, min_length=1, description="Etsy API key (keystring)")
    shared_secret: str | None = Field(None, min_length=1, description="Etsy shared secret")
    access_token: str | None = Field(None, min_length=1, description="Etsy OAuth access token")
    refresh_token: str | None = Field(None, min_length=1, description="Etsy OAuth refresh token")
    shop_id: str | None = Field(None, min_length=1, description="Etsy shop ID")


class EtsySettingsResponse(BaseModel):
    """Schema for Etsy settings response (with masked credentials)."""

    enabled: bool = Field(default=False, description="Whether Etsy integration is enabled")
    is_configured: bool = Field(
        default=False, description="Whether all required credentials are set"
    )
    api_key_masked: str | None = Field(None, description="Masked API key (last 4 chars)")
    shared_secret_masked: str | None = Field(None, description="Masked shared secret (last 4 chars)")
    access_token_masked: str | None = Field(None, description="Masked access token (last 4 chars)")
    refresh_token_set: bool = Field(default=False, description="Whether refresh token is set")
    shop_id: str | None = Field(None, description="Etsy shop ID")
    shop_name: str | None = Field(None, description="Etsy shop name (from last connection test)")
    updated_at: datetime | None = Field(None, description="Last update timestamp")


class EtsyConnectionTest(BaseModel):
    """Schema for Etsy connection test response."""

    success: bool = Field(..., description="Whether the connection test succeeded")
    message: str = Field(..., description="Test result message")
    shop_name: str | None = Field(None, description="Etsy shop name if found")
    shop_url: str | None = Field(None, description="Etsy shop URL if found")


# =============================================================================
# Square Settings Schemas
# =============================================================================


class SquareSettingsUpdate(BaseModel):
    """Schema for updating Square payment settings."""

    enabled: bool | None = Field(None, description="Enable/disable Square payments")
    environment: Literal["sandbox", "production"] | None = Field(
        None, description="Square environment (sandbox or production)"
    )
    access_token: str | None = Field(None, min_length=1, description="Square access token")
    app_id: str | None = Field(None, min_length=1, description="Square application ID")
    location_id: str | None = Field(None, min_length=1, description="Square location ID")


class SquareSettingsResponse(BaseModel):
    """Schema for Square settings response (with masked credentials)."""

    enabled: bool = Field(default=False, description="Whether Square payments are enabled")
    environment: Literal["sandbox", "production"] = Field(
        default="sandbox", description="Square environment"
    )
    is_configured: bool = Field(
        default=False, description="Whether all required credentials are set"
    )
    access_token_masked: str | None = Field(None, description="Masked access token (last 4 chars)")
    app_id: str | None = Field(None, description="Square application ID")
    location_id_masked: str | None = Field(None, description="Masked location ID (last 4 chars)")
    updated_at: datetime | None = Field(None, description="Last update timestamp")


class SquareConnectionTest(BaseModel):
    """Schema for Square connection test response."""

    success: bool = Field(..., description="Whether the connection test succeeded")
    message: str = Field(..., description="Test result message")
    environment: str | None = Field(None, description="Environment tested")
    location_name: str | None = Field(None, description="Square location name if found")


# =============================================================================
# Tenant Settings Schemas
# =============================================================================


class TenantResponse(BaseModel):
    """Schema for tenant details response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Tenant UUID")
    name: str = Field(..., description="Tenant/organization name")
    slug: str = Field(..., description="URL-safe identifier")
    tenant_type: TenantType = Field(..., description="Tenant business type")
    description: str | None = Field(None, description="Tenant description")
    is_active: bool = Field(..., description="Whether the tenant is active")
    settings: TenantSettings | dict = Field(default_factory=dict, description="Tenant settings")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class TenantUpdate(BaseModel):
    """Schema for updating tenant details."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Tenant name")
    description: str | None = Field(None, max_length=500, description="Tenant description")
    tenant_type: TenantType | None = Field(None, description="Tenant business type")


# =============================================================================
# Shop Settings Schemas
# =============================================================================


class ShopSettingsResponse(BaseModel):
    """Schema for shop settings response."""

    enabled: bool = Field(default=False, description="Shop is publicly accessible")
    shop_name: str | None = Field(None, description="Public shop name")
    shop_url_slug: str | None = Field(None, description="URL slug for subdomain")
    custom_domain: str | None = Field(None, description="Custom domain")
    custom_domain_verified: bool = Field(default=False, description="DNS verified")
    order_prefix: str | None = Field(None, description="Order number prefix")
    tagline: str | None = Field(None, description="Shop tagline/slogan")
    about_text: str | None = Field(None, description="About the shop")
    contact_email: str | None = Field(None, description="Contact email")
    social_links: dict[str, str] = Field(default_factory=dict, description="Social links")
    shipping_info: str | None = Field(None, description="Shipping information")
    return_policy: str | None = Field(None, description="Return policy")


class ShopSettingsUpdate(BaseModel):
    """Schema for updating shop settings. All fields optional for partial updates."""

    enabled: bool | None = Field(None, description="Shop is publicly accessible")
    shop_name: str | None = Field(None, max_length=100, description="Public shop name")
    shop_url_slug: str | None = Field(
        None, max_length=50, pattern=r"^[a-z0-9-]+$", description="URL slug (lowercase, hyphens)"
    )
    order_prefix: str | None = Field(
        None, max_length=10, pattern=r"^[A-Z0-9]+$", description="Order prefix (uppercase)"
    )
    tagline: str | None = Field(None, max_length=200, description="Shop tagline")
    about_text: str | None = Field(None, max_length=5000, description="About text")
    contact_email: str | None = Field(None, description="Contact email")
    social_links: dict[str, str] | None = Field(None, description="Social media links")
    shipping_info: str | None = Field(None, max_length=5000, description="Shipping info")
    return_policy: str | None = Field(None, max_length=5000, description="Return policy")


# =============================================================================
# Custom Domain Schemas
# =============================================================================


class CustomDomainRequest(BaseModel):
    """Schema for initiating custom domain setup."""

    domain: str = Field(
        ...,
        min_length=4,
        max_length=253,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$",
        description="Custom domain (e.g., shop.example.com)",
    )


class CustomDomainStatusResponse(BaseModel):
    """Schema for custom domain status response."""

    has_custom_domain: bool = Field(..., description="Whether a custom domain is configured")
    domain: str | None = Field(None, description="The custom domain")
    verified: bool = Field(default=False, description="Whether DNS is verified")
    verification_started_at: str | None = Field(None, description="When verification started")
    verification_completed_at: str | None = Field(None, description="When verification completed")
    cname_target: str | None = Field(None, description="Expected CNAME target")
    txt_record_host: str | None = Field(None, description="TXT record hostname")


class CustomDomainInitResponse(BaseModel):
    """Schema for custom domain initialization response."""

    domain: str = Field(..., description="The custom domain")
    verification_token: str = Field(..., description="Token for TXT record")
    cname_target: str = Field(..., description="CNAME target (shops.batchivo.com)")
    txt_record_host: str = Field(..., description="TXT record hostname")
    instructions: dict[str, str] = Field(..., description="Setup instructions")


class CustomDomainVerifyResponse(BaseModel):
    """Schema for domain verification response."""

    success: bool = Field(..., description="Whether verification succeeded")
    cname_verified: bool = Field(default=False, description="CNAME record verified")
    txt_verified: bool = Field(default=False, description="TXT record verified")
    domain: str | None = Field(None, description="The verified domain")
    message: str | None = Field(None, description="Result message")
    error: str | None = Field(None, description="Error message if failed")


# =============================================================================
# Branding Settings Schemas
# =============================================================================


class BrandingSettingsResponse(BaseModel):
    """Schema for branding settings response."""

    logo_url: str | None = Field(None, description="URL to tenant logo")
    favicon_url: str | None = Field(None, description="URL to favicon")
    primary_color: str = Field(default="#3B82F6", description="Primary brand color (hex)")
    accent_color: str = Field(default="#10B981", description="Accent/secondary color (hex)")
    font_family: str | None = Field(None, description="Custom font family")
    updated_at: str | None = Field(None, description="Last update timestamp")


class BrandingSettingsUpdate(BaseModel):
    """Schema for updating branding settings. All fields optional for partial updates."""

    logo_url: str | None = Field(None, max_length=500, description="URL to logo image")
    favicon_url: str | None = Field(None, max_length=500, description="URL to favicon")
    primary_color: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Primary color (6-digit hex, e.g., #3B82F6)",
    )
    accent_color: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Accent color (6-digit hex, e.g., #10B981)",
    )
    font_family: str | None = Field(None, max_length=100, description="Custom font family name")


# =============================================================================
# Tenant Member Schemas
# =============================================================================


class TenantMemberResponse(BaseModel):
    """Schema for tenant member response."""

    id: UUID = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    full_name: str | None = Field(None, description="User's full name")
    role: UserRole = Field(..., description="User's role in the tenant")
    is_active: bool = Field(..., description="Whether the user is active")
    joined_at: datetime = Field(..., description="When the user joined the tenant")

    class Config:
        from_attributes = True


class TenantMemberInvite(BaseModel):
    """Schema for inviting a user to a tenant."""

    email: EmailStr = Field(..., description="Email address to invite")
    role: UserRole = Field(
        default=UserRole.MEMBER, description="Role to assign to the invited user"
    )


class TenantMemberRoleUpdate(BaseModel):
    """Schema for updating a member's role."""

    role: UserRole = Field(..., description="New role for the member")


class TenantMemberListResponse(BaseModel):
    """Schema for list of tenant members."""

    members: list[TenantMemberResponse] = Field(..., description="List of tenant members")
    total: int = Field(..., description="Total number of members")
