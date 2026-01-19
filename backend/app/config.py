"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known weak secrets that should be rejected
WEAK_SECRETS = [
    "dev-secret-key-change-in-production",
    "secret",
    "change-me",
    "changeme",
    "password",
    "your-secret-key",
    "supersecret",
]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Batchivo"
    environment: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    # Note: Using psycopg (not asyncpg) due to Python 3.14 compatibility
    database_url: str = "postgresql+psycopg://batchivo:batchivo@localhost:5432/batchivo"

    # Row-Level Security (RLS)
    # When enabled, uses app_user role which has RLS policies enforced
    rls_enabled: bool = False  # Enable in production after RLS policies are set up
    rls_database_url: str = ""  # Connection string for app_user role (set in production)

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Caching
    cache_enabled: bool = True
    cache_default_ttl: int = 300  # 5 minutes

    # CORS - add your tenant domains via CORS_ORIGINS environment variable
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "https://batchivo.com",
        "https://dev.batchivo.com",
    ]
    cors_allow_credentials: bool = True

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "batchivo-backend"
    otel_environment: str = "development"
    enable_tracing: bool = True
    enable_metrics: bool = True

    # Celery (background jobs)
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Storage
    storage_type: Literal["local", "s3"] = "local"
    storage_path: str = "./uploads"
    storage_s3_bucket: str = "batchivo-images"
    storage_s3_region: str = "us-east-1"
    storage_s3_endpoint: str = ""  # MinIO endpoint, empty for AWS S3
    storage_s3_access_key: str = ""
    storage_s3_secret_key: str = ""

    # Security
    # SECURITY: No default - must be set via SECRET_KEY environment variable
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    secret_key: str
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Square Payments (optional - for shop checkout)
    square_app_id: str = ""  # Application ID for Web Payments SDK
    square_access_token: str = ""
    square_location_id: str = ""
    square_environment: Literal["sandbox", "production"] = "sandbox"
    square_webhook_signature_key: str = ""

    # Email (Brevo) - configure via environment variables
    brevo_api_key: str = ""
    email_from_address: str = "noreply@example.com"
    email_from_name: str = "Batchivo"
    frontend_base_url: str = "http://localhost:5173"  # Base URL for email links

    # Sentry Error Monitoring
    sentry_dsn: str = ""  # Sentry DSN for error tracking (leave empty to disable)
    sentry_traces_sample_rate: float = 0.1  # Performance monitoring sample rate

    # Shop Branding - configure for your shop's email templates
    shop_name: str = "Your Shop"  # Display name in emails
    shop_tagline: str = "Welcome to our shop"  # Tagline shown in email headers
    shop_website_url: str = "http://localhost:5173"  # Website URL for email footers
    shop_orders_email: str = "orders@example.com"  # Email for order inquiries
    shop_support_email: str = "support@example.com"  # Email for contact form notifications
    shop_social_handle: str = ""  # Social media handle (e.g., "@yourshop")
    shop_brand_color: str = "#6366f1"  # Primary brand color (hex) for emails

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        """Validate that secret_key meets security requirements."""
        if not self.secret_key:
            raise ValueError(
                "SECRET_KEY environment variable is required. "
                'Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

        if len(self.secret_key) < 32:
            raise ValueError(
                f"SECRET_KEY must be at least 32 characters (got {len(self.secret_key)}). "
                'Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

        if self.secret_key.lower() in WEAK_SECRETS:
            raise ValueError(
                "SECRET_KEY is using a known weak default value. "
                'Generate a secure key with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

        return self

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    @property
    def effective_database_url(self) -> str:
        """
        Get the effective database URL based on RLS configuration.

        When RLS is enabled and rls_database_url is set, uses the app_user
        connection which has RLS policies enforced. Otherwise, uses the
        regular database_url (typically superuser for migrations).
        """
        if self.rls_enabled and self.rls_database_url:
            return self.rls_database_url
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
