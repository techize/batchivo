"""Test API endpoints to verify authentication and tenant context."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentTenant, CurrentUser, require_role
from app.database import get_db
from app.models.material import MaterialType
from app.services.email_service import get_email_service

router = APIRouter()


class TestEmailRequest(BaseModel):
    """Request body for test email."""

    to_email: EmailStr


@router.post("/email")
async def send_test_email(
    request: TestEmailRequest,
    user: CurrentUser,
    tenant: CurrentTenant,
) -> dict:
    """
    Send a test email to verify Resend configuration.

    Requires authentication. Sends a test order confirmation email.
    """
    email_service = get_email_service()

    if not email_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured - RESEND_API_KEY not set",
        )

    # Send test order confirmation
    success = email_service.send_order_confirmation(
        to_email=request.to_email,
        customer_name="Test Customer",
        order_number="TEST-20251229-001",
        order_items=[
            {"name": "Test Dragon - Ember", "quantity": 1, "price": 29.99},
            {"name": "Test Dinosaur - Rex", "quantity": 2, "price": 19.99},
        ],
        subtotal=69.97,
        shipping_cost=4.99,
        total=74.96,
        shipping_address={
            "address_line1": "123 Test Street",
            "city": "London",
            "postcode": "SW1A 1AA",
            "country": "United Kingdom",
        },
    )

    if success:
        return {
            "success": True,
            "message": f"Test email sent to {request.to_email}",
            "from": f"{email_service.from_name} <{email_service.from_address}>",
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to send test email - check logs for details",
        )


@router.get("/me")
async def get_current_user_info(
    user: CurrentUser,
    tenant: CurrentTenant,
) -> dict:
    """
    Get current user and tenant information.

    This endpoint demonstrates:
    - User authentication working
    - Tenant context working
    - Auto-creation of dev users/tenants

    No authentication required in development mode.
    """
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
        },
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "is_active": tenant.is_active,
        },
        "message": "Authentication and tenant context working! 🎉",
    }


@router.get("/materials")
async def list_material_types(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all material types (reference data).

    This endpoint demonstrates:
    - Database queries working
    - Reference data accessible

    No authentication required (public reference data).
    """
    result = await db.execute(
        select(MaterialType)
        .where(MaterialType.is_active.is_(True))  # noqa: E712
        .order_by(MaterialType.name)
    )
    materials = result.scalars().all()

    return {
        "count": len(materials),
        "materials": [
            {
                "id": str(m.id),
                "name": m.name,
                "code": m.code,
                "density": m.typical_density,
                "min_temp": m.min_temp,
                "max_temp": m.max_temp,
            }
            for m in materials
        ],
    }


@router.get("/admin-only")
async def admin_only_endpoint(
    user: CurrentUser,
    tenant: CurrentTenant,
    is_authorized: bool = Depends(lambda u, t, db: require_role(u, t, db, "admin")),
) -> dict:
    """
    Admin-only endpoint to test role-based access control.

    Requires: admin or owner role
    """
    return {
        "message": "You have admin access!",
        "user_email": user.email,
        "tenant_name": tenant.name,
    }
