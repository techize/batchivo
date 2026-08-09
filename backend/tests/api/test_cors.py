"""CORS behavior for browser-facing API requests."""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_shop_preflight_allows_sentry_trace_headers(
    unauthenticated_client: AsyncClient,
):
    """Browser preflights with Sentry tracing headers must not block shop product loads."""
    response = await unauthenticated_client.options(
        "/api/v1/shop/products?sort=newest&limit=200",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-shop-hostname,sentry-trace,baggage",
        },
    )

    assert response.status_code == 200
    allow_headers = response.headers["access-control-allow-headers"].lower()
    assert "sentry-trace" in allow_headers
    assert "baggage" in allow_headers
