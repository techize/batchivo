"""Tests: public shop product endpoints set CDN-friendly Cache-Control headers (MYS-488)."""
from decimal import Decimal
from uuid import uuid4
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.product import Product
from app.models.product_pricing import ProductPricing
from app.models.sales_channel import SalesChannel


@pytest_asyncio.fixture
async def channel(db_session, test_tenant):
    sc = SalesChannel(id=uuid4(), tenant_id=test_tenant.id, name="Shop",
        platform_type="online_shop", is_active=True)
    db_session.add(sc)
    await db_session.commit()
    await db_session.refresh(sc)
    return sc


@pytest_asyncio.fixture
async def product(db_session, test_tenant, channel):
    p = Product(id=uuid4(), tenant_id=test_tenant.id, sku="CACHE-TEST-001",
        name="Cache Test Dragon", is_active=True, shop_visible=True,
        seo_slug="cache-test-dragon")
    db_session.add(p)
    await db_session.commit()
    pricing = ProductPricing(id=uuid4(), product_id=p.id,
        sales_channel_id=channel.id, list_price=Decimal("19.99"))
    db_session.add(pricing)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest_asyncio.fixture
async def client(db_session, test_tenant, channel):
    from app.auth.dependencies import get_shop_sales_channel
    from app.database import get_db
    async def override_db():
        yield db_session
    async def override_ctx():
        return (test_tenant, channel)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_shop_sales_channel] = override_ctx
    app.state.limiter.enabled = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_products_list_has_cache_control(client):
    resp = await client.get("/api/v1/shop/products")
    assert resp.status_code == 200
    cc = resp.headers.get("cache-control", "")
    assert "public" in cc
    assert "s-maxage=60" in cc


@pytest.mark.anyio
async def test_products_list_with_filter_has_cache_control(client, product):
    resp = await client.get("/api/v1/shop/products?category=dragons")
    assert resp.status_code == 200
    cc = resp.headers.get("cache-control", "")
    assert "public" in cc
    assert "s-maxage=60" in cc


@pytest.mark.anyio
async def test_product_detail_has_cache_control(client, product):
    resp = await client.get(f"/api/v1/shop/products/{product.seo_slug}")
    assert resp.status_code == 200
    cc = resp.headers.get("cache-control", "")
    assert "public" in cc
    assert "s-maxage=300" in cc


@pytest.mark.anyio
async def test_product_detail_not_found_no_cache(client):
    resp = await client.get("/api/v1/shop/products/nonexistent-slug-xyz")
    assert resp.status_code == 404
    cc = resp.headers.get("cache-control", "")
    assert "s-maxage" not in cc
