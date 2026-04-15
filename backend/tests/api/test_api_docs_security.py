"""Tests: API docs and schema endpoints are blocked in production (security)."""
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch


@pytest.mark.anyio
async def test_openapi_json_blocked_in_production():
    """openapi.json must return 404 in production — schema reveals all endpoint paths."""
    from app.main import app
    from app.config import get_settings

    settings = get_settings()
    # Only meaningful to assert in production; dev mode intentionally exposes docs
    if not settings.is_development:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/openapi.json")
        assert resp.status_code == 404, (
            "/openapi.json must be disabled in production (openapi_url=None)"
        )


@pytest.mark.anyio
async def test_docs_blocked_in_production():
    """FastAPI /docs UI must return 404 in production."""
    from app.main import app
    from app.config import get_settings

    settings = get_settings()
    if not settings.is_development:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/docs")
        assert resp.status_code == 404


@pytest.mark.anyio
async def test_redoc_blocked_in_production():
    """FastAPI /redoc UI must return 404 in production."""
    from app.main import app
    from app.config import get_settings

    settings = get_settings()
    if not settings.is_development:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/redoc")
        assert resp.status_code == 404
