"""Shipping rates API endpoints.

Provides shipping rate calculations and postcode validation.
"""

from fastapi import APIRouter, Depends

from app.schemas.shipping import (
    PostcodeValidationResponse,
    ShippingRateRequest,
    ShippingRatesResponse,
)
from app.services.shipping_service import ShippingService, get_shipping_service

router = APIRouter()


@router.post("/rates", response_model=ShippingRatesResponse)
async def get_shipping_rates(
    request: ShippingRateRequest,
    shipping_service: ShippingService = Depends(get_shipping_service),
):
    """
    Get available shipping rates for a UK postcode.

    Returns a list of shipping options with prices. Automatically applies:
    - Highland/Island surcharges for remote UK areas
    - Free shipping on orders over the threshold

    **Note**: Prices are in pence (e.g., 395 = £3.95)
    """
    return await shipping_service.get_shipping_rates(
        postcode=request.postcode,
        weight_grams=request.weight_grams,
        cart_total_pence=request.cart_total_pence,
    )


@router.get("/validate-postcode/{postcode}", response_model=PostcodeValidationResponse)
async def validate_postcode(
    postcode: str,
    shipping_service: ShippingService = Depends(get_shipping_service),
):
    """
    Validate a UK postcode.

    Returns:
    - Whether the postcode is valid
    - The normalized postcode format
    - The postal area and region
    - Whether it's a Highland/Island area (surcharge applies)
    """
    return shipping_service.validate_postcode(postcode)


@router.get("/methods")
async def list_shipping_methods(
    shipping_service: ShippingService = Depends(get_shipping_service),
):
    """
    List all available shipping methods.

    Returns the base shipping options without postcode-specific pricing.
    Use the /rates endpoint for accurate pricing with a specific postcode.
    """
    return {
        "methods": [
            {
                "id": opt.id,
                "name": opt.name,
                "carrier": opt.carrier,
                "description": opt.description,
                "base_price_pence": opt.price_pence,
                "estimated_days": opt.estimated_days_display,
                "is_tracked": opt.is_tracked,
                "is_signed": opt.is_signed,
            }
            for opt in shipping_service.STANDARD_OPTIONS
        ],
        "free_shipping_threshold_pence": shipping_service.FREE_SHIPPING_THRESHOLD_PENCE,
        "highland_island_surcharge_pence": shipping_service.HIGHLAND_ISLAND_SURCHARGE_PENCE,
    }
