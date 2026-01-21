"""Newsletter subscription API endpoints.

Public endpoint for newsletter signup - no authentication required.
Uses Brevo (formerly Sendinblue) for contact management.
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate limiter for newsletter endpoint (prevent abuse)
limiter = Limiter(key_func=get_remote_address)


class NewsletterSubscribeRequest(BaseModel):
    """Request model for newsletter subscription."""

    email: EmailStr
    first_name: Optional[str] = None
    source: Optional[str] = None  # Track where signup came from (e.g., "footer", "popup")

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize first name - remove special characters."""
        if v is None:
            return None
        # Remove any HTML/script tags and limit length
        clean = re.sub(r"[<>\"']", "", v.strip())
        return clean[:50] if clean else None


class NewsletterSubscribeResponse(BaseModel):
    """Response model for newsletter subscription."""

    success: bool
    message: str


@router.post(
    "/subscribe",
    response_model=NewsletterSubscribeResponse,
    status_code=status.HTTP_200_OK,
    summary="Subscribe to newsletter",
    description="Subscribe an email address to the newsletter. No authentication required.",
)
@limiter.limit("5/minute")  # Rate limit: 5 requests per minute per IP
async def subscribe_newsletter(
    request: Request,
    body: NewsletterSubscribeRequest,
) -> NewsletterSubscribeResponse:
    """
    Subscribe to the newsletter.

    This is a public endpoint that allows visitors to subscribe to the shop's
    newsletter. The email is added to Brevo contact list.

    Rate limited to 5 requests per minute per IP to prevent abuse.
    """
    email_service = get_email_service()

    # Build attributes for Brevo contact
    attributes = {}
    if body.first_name:
        attributes["FIRSTNAME"] = body.first_name
    if body.source:
        attributes["SIGNUP_SOURCE"] = body.source

    # Subscribe to newsletter
    success, message = await email_service.subscribe_newsletter(
        email=body.email,
        attributes=attributes if attributes else None,
    )

    if not success:
        # Log the failure but return a generic message to the user
        logger.warning(f"Newsletter subscription failed for {body.email}: {message}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to process subscription at this time. Please try again later.",
        )

    return NewsletterSubscribeResponse(
        success=True,
        message="Thank you for subscribing! You'll receive our latest updates soon.",
    )
