"""Tests for the shop sitemap endpoint."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.product import Product
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant


@pytest_asyncio.fixture
async def sales_channel(db_session: AsyncSession, test_tenant: Tenant) -> SalesChannel:
    channel = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Sitemap Test Channel",
        platform_type="online_shop",
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
async def shop_product_with_slug(
    db_session: AsyncSession, test_tenant: Tenant, sales_channel: SalesChannel
) -> Product:
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="SITEMAP-001",
        name="Caelith Sky Dragon",
        description="A sky dragon for sitemap testing",
        is_active=True,
        shop_visible=True,
        units_in_stock=0,
        print_to_order=True,
        seo_slug="caelith-sky-dragon",
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_product_no_slug(
    db_session: AsyncSession, test_tenant: Tenant, sales_channel: SalesChannel
) -> Product:
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="SITEMAP-002",
        name="No Slug Dragon",
        description="A dragon with no seo_slug",
        is_active=True,
        shop_visible=True,
        units_in_stock=0,
        print_to_order=True,
        seo_slug=None,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def hidden_product(db_session: AsyncSession, test_tenant: Tenant) -> Product:
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="SITEMAP-003",
        name="Hidden Dragon",
        description="Not shop visible",
        is_active=True,
        shop_visible=False,
        units_in_stock=0,
        seo_slug="hidden-dragon",
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_client(db_session: AsyncSession, test_tenant: Tenant, sales_channel: SalesChannel):
    from app.auth.dependencies import get_shop_sales_channel
    from app.database import get_db

    async def override_get_db():
        yield db_session

    async def override_shop_context():
        return (test_tenant, sales_channel)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shop_sales_channel] = override_shop_context
    app.state.limiter.enabled = False

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_sitemap_returns_xml(shop_client: AsyncClient, shop_product_with_slug: Product):
    """Sitemap returns valid XML with correct content-type."""
    response = await shop_client.get("/api/v1/shop/sitemap.xml")
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert response.text.startswith("<?xml")
    assert "<urlset" in response.text


@pytest.mark.anyio
async def test_sitemap_includes_static_pages(shop_client: AsyncClient):
    """Sitemap includes key static pages."""
    response = await shop_client.get("/api/v1/shop/sitemap.xml")
    assert response.status_code == 200
    body = response.text
    assert "https://www.mystmereforge.co.uk/" in body
    assert "https://www.mystmereforge.co.uk/shop" in body
    assert "https://www.mystmereforge.co.uk/dragons" in body
    assert "https://www.mystmereforge.co.uk/blog" in body
    assert "https://www.mystmereforge.co.uk/about" in body


@pytest.mark.anyio
async def test_sitemap_includes_blog_posts(shop_client: AsyncClient):
    """Sitemap includes known blog post slugs."""
    response = await shop_client.get("/api/v1/shop/sitemap.xml")
    assert response.status_code == 200
    body = response.text
    assert "/blog/what-is-an-articulated-dragon" in body
    assert "/blog/caelith-the-sky-crystal-dragon-of-the-mystmere-valley" in body


@pytest.mark.anyio
async def test_sitemap_uses_seo_slug_for_products(
    shop_client: AsyncClient, shop_product_with_slug: Product
):
    """Products with seo_slug appear as /products/{slug} in sitemap."""
    response = await shop_client.get("/api/v1/shop/sitemap.xml")
    assert response.status_code == 200
    assert "/products/caelith-sky-dragon" in response.text


@pytest.mark.anyio
async def test_sitemap_falls_back_to_uuid_when_no_slug(
    shop_client: AsyncClient, shop_product_no_slug: Product
):
    """Products without seo_slug fall back to UUID path in sitemap."""
    response = await shop_client.get("/api/v1/shop/sitemap.xml")
    assert response.status_code == 200
    assert f"/products/{shop_product_no_slug.id}" in response.text


@pytest.mark.anyio
async def test_sitemap_excludes_hidden_products(shop_client: AsyncClient, hidden_product: Product):
    """Products with shop_visible=False are excluded from the sitemap."""
    response = await shop_client.get("/api/v1/shop/sitemap.xml")
    assert response.status_code == 200
    assert "hidden-dragon" not in response.text
    assert str(hidden_product.id) not in response.text
