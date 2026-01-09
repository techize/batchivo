"""DNS verification service for custom domain setup."""

import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

import dns.resolver
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# Target for CNAME verification
SHOPS_DOMAIN = "shops.nozzly.app"


class DomainVerificationService:
    """Service for verifying custom domain DNS configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_verification_token(self) -> str:
        """Generate a unique verification token for domain ownership.

        Returns:
            A URL-safe token prefixed with 'nozzly-verify-'
        """
        return f"nozzly-verify-{secrets.token_urlsafe(32)}"

    async def verify_cname(
        self, domain: str, expected_target: str = SHOPS_DOMAIN
    ) -> tuple[bool, str | None]:
        """Verify that a domain's CNAME record points to the expected target.

        Args:
            domain: The custom domain to verify
            expected_target: The expected CNAME target (default: shops.nozzly.app)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            answers = dns.resolver.resolve(domain, "CNAME")
            for rdata in answers:
                target = str(rdata.target).rstrip(".")
                if target == expected_target:
                    logger.info(f"CNAME verification passed for {domain} -> {target}")
                    return True, None

            # CNAME exists but points elsewhere
            actual_targets = [str(rdata.target).rstrip(".") for rdata in answers]
            error_msg = f"CNAME points to {', '.join(actual_targets)} instead of {expected_target}"
            logger.warning(f"CNAME verification failed for {domain}: {error_msg}")
            return False, error_msg

        except dns.resolver.NXDOMAIN:
            error_msg = "Domain not found (NXDOMAIN)"
            logger.warning(f"CNAME verification failed for {domain}: {error_msg}")
            return False, error_msg

        except dns.resolver.NoAnswer:
            error_msg = "No CNAME record found"
            logger.warning(f"CNAME verification failed for {domain}: {error_msg}")
            return False, error_msg

        except dns.resolver.NoNameservers:
            error_msg = "No nameservers available"
            logger.warning(f"CNAME verification failed for {domain}: {error_msg}")
            return False, error_msg

        except dns.exception.Timeout:
            error_msg = "DNS query timed out"
            logger.warning(f"CNAME verification failed for {domain}: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"DNS query error: {str(e)}"
            logger.error(f"CNAME verification failed for {domain}: {error_msg}")
            return False, error_msg

    async def verify_txt(self, domain: str, expected_token: str) -> tuple[bool, str | None]:
        """Verify that a TXT record contains the expected verification token.

        Looks for a TXT record at _nozzly-verify.{domain}

        Args:
            domain: The custom domain to verify
            expected_token: The verification token to look for

        Returns:
            Tuple of (success, error_message)
        """
        txt_hostname = f"_nozzly-verify.{domain}"

        try:
            answers = dns.resolver.resolve(txt_hostname, "TXT")
            for rdata in answers:
                # TXT records can be multi-part, so join all parts
                txt_value = "".join(part.decode() for part in rdata.strings)
                if expected_token in txt_value:
                    logger.info(f"TXT verification passed for {domain}")
                    return True, None

            # TXT record exists but doesn't contain our token
            error_msg = f"TXT record at {txt_hostname} does not contain verification token"
            logger.warning(f"TXT verification failed for {domain}: {error_msg}")
            return False, error_msg

        except dns.resolver.NXDOMAIN:
            error_msg = f"No DNS record found at {txt_hostname}"
            logger.warning(f"TXT verification failed for {domain}: {error_msg}")
            return False, error_msg

        except dns.resolver.NoAnswer:
            error_msg = f"No TXT record found at {txt_hostname}"
            logger.warning(f"TXT verification failed for {domain}: {error_msg}")
            return False, error_msg

        except dns.resolver.NoNameservers:
            error_msg = "No nameservers available"
            logger.warning(f"TXT verification failed for {domain}: {error_msg}")
            return False, error_msg

        except dns.exception.Timeout:
            error_msg = "DNS query timed out"
            logger.warning(f"TXT verification failed for {domain}: {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"DNS query error: {str(e)}"
            logger.error(f"TXT verification failed for {domain}: {error_msg}")
            return False, error_msg

    async def initiate_domain_verification(self, tenant_id: UUID, domain: str) -> dict:
        """Start the custom domain verification process for a tenant.

        Generates a verification token and stores it in tenant settings.

        Args:
            tenant_id: The tenant's UUID
            domain: The custom domain to verify

        Returns:
            Dict with verification instructions
        """
        # Generate verification token
        token = self.generate_verification_token()

        # Get tenant and update settings
        tenant = await self._get_tenant(tenant_id)
        current_settings = dict(tenant.settings)
        shop_settings = dict(current_settings.get("shop", {}))

        # Store pending domain verification
        shop_settings["custom_domain"] = domain
        shop_settings["custom_domain_verified"] = False
        shop_settings["verification_token"] = token
        shop_settings["verification_started_at"] = datetime.now(timezone.utc).isoformat()

        current_settings["shop"] = shop_settings
        await self._update_tenant_settings(tenant_id, current_settings)

        return {
            "domain": domain,
            "verification_token": token,
            "cname_target": SHOPS_DOMAIN,
            "txt_record_host": f"_nozzly-verify.{domain}",
            "instructions": {
                "step_1": f"Add a CNAME record for '{domain}' pointing to '{SHOPS_DOMAIN}'",
                "step_2": f"Add a TXT record at '_nozzly-verify.{domain}' with value '{token}'",
                "step_3": "Wait for DNS propagation (can take up to 48 hours)",
                "step_4": "Call the verify endpoint to complete verification",
            },
        }

    async def complete_domain_verification(self, tenant_id: UUID) -> dict:
        """Complete the domain verification by checking DNS records.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            Dict with verification result
        """
        tenant = await self._get_tenant(tenant_id)
        shop_settings = tenant.settings.get("shop", {})

        domain = shop_settings.get("custom_domain")
        token = shop_settings.get("verification_token")

        if not domain:
            return {
                "success": False,
                "error": "No custom domain configured. Start verification first.",
            }

        if not token:
            return {
                "success": False,
                "error": "No verification token found. Start verification first.",
            }

        # Check CNAME
        cname_ok, cname_error = await self.verify_cname(domain)
        if not cname_ok:
            return {
                "success": False,
                "cname_verified": False,
                "txt_verified": False,
                "error": f"CNAME verification failed: {cname_error}",
            }

        # Check TXT
        txt_ok, txt_error = await self.verify_txt(domain, token)
        if not txt_ok:
            return {
                "success": False,
                "cname_verified": True,
                "txt_verified": False,
                "error": f"TXT verification failed: {txt_error}",
            }

        # Both passed - update tenant settings
        current_settings = dict(tenant.settings)
        shop_settings = dict(current_settings.get("shop", {}))
        shop_settings["custom_domain_verified"] = True
        shop_settings["verification_completed_at"] = datetime.now(timezone.utc).isoformat()
        # Keep the token for potential re-verification

        current_settings["shop"] = shop_settings
        await self._update_tenant_settings(tenant_id, current_settings)

        logger.info(f"Domain verification completed for tenant {tenant_id}: {domain}")

        return {
            "success": True,
            "cname_verified": True,
            "txt_verified": True,
            "domain": domain,
            "message": f"Domain {domain} has been verified and is now active.",
        }

    async def remove_custom_domain(self, tenant_id: UUID) -> dict:
        """Remove custom domain configuration from a tenant.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            Dict with result
        """
        tenant = await self._get_tenant(tenant_id)
        current_settings = dict(tenant.settings)
        shop_settings = dict(current_settings.get("shop", {}))

        old_domain = shop_settings.get("custom_domain")

        # Clear domain-related settings
        shop_settings["custom_domain"] = None
        shop_settings["custom_domain_verified"] = False
        shop_settings["verification_token"] = None
        shop_settings["verification_started_at"] = None
        shop_settings["verification_completed_at"] = None

        current_settings["shop"] = shop_settings
        await self._update_tenant_settings(tenant_id, current_settings)

        logger.info(f"Custom domain removed for tenant {tenant_id}: {old_domain}")

        return {
            "success": True,
            "message": f"Custom domain {old_domain} has been removed.",
        }

    async def get_verification_status(self, tenant_id: UUID) -> dict:
        """Get the current domain verification status for a tenant.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            Dict with current status
        """
        tenant = await self._get_tenant(tenant_id)
        shop_settings = tenant.settings.get("shop", {})

        domain = shop_settings.get("custom_domain")

        if not domain:
            return {
                "has_custom_domain": False,
                "domain": None,
                "verified": False,
            }

        return {
            "has_custom_domain": True,
            "domain": domain,
            "verified": shop_settings.get("custom_domain_verified", False),
            "verification_started_at": shop_settings.get("verification_started_at"),
            "verification_completed_at": shop_settings.get("verification_completed_at"),
            "cname_target": SHOPS_DOMAIN,
            "txt_record_host": f"_nozzly-verify.{domain}",
        }

    async def _get_tenant(self, tenant_id: UUID) -> Tenant:
        """Get a tenant by ID.

        Args:
            tenant_id: The tenant's UUID

        Returns:
            The Tenant object

        Raises:
            ValueError: If tenant not found
        """
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant not found: {tenant_id}")

        return tenant

    async def _update_tenant_settings(self, tenant_id: UUID, settings: dict) -> None:
        """Update tenant settings JSON field.

        Args:
            tenant_id: The tenant's UUID
            settings: The new settings dict
        """
        stmt = (
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(settings=settings, updated_at=datetime.now(timezone.utc))
        )
        await self.db.execute(stmt)
        await self.db.commit()


# Factory function for dependency injection
async def get_domain_verification_service(
    db: AsyncSession,
) -> DomainVerificationService:
    """Create a DomainVerificationService instance."""
    return DomainVerificationService(db)
