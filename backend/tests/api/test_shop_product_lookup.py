"""Tests for shop product lookup by UUID and seo_slug."""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.product import Product
from app.models.product_pricing import ProductPricing
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant


@pytest_asyncio.fixture
async def sales_channel(db_session: AsyncSession, test_tenant: Tenant) -> SalesChannel:
    """Create a sales channel for pricing."""
    channel = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Mystmereforge Test",
        platform_type="online_shop",
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
async def shop_product(
    db_session: AsyncSession, test_tenant: Tenant, sales_channel: SalesChannel
) -> Product:
    """Create a shop-visible product with a seo_slug."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="TEST-SLUG-001",
        name="Frost the Ice Dragon",
        description="A test ice dragon product",
        is_active=True,
        shop_visible=True,
        units_in_stock=0,
        print_to_order=True,
        seo_slug="frost-the-ice-dragon",
    )
    db_session.add(product)
    await db_session.commit()

    pricing = ProductPricing(
        id=uuid4(),
        product_id=product.id,
        sales_channel_id=sales_channel.id,
        list_price=Decimal("24.99"),
    )
    db_session.add(pricing)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_client(db_session: AsyncSession, test_tenant: Tenant, sales_channel: SalesChannel):
    """HTTP client with DB dependency overridden."""
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
async def test_get_product_by_uuid(shop_client: AsyncClient, shop_product: Product):
    """GET /shop/products/{uuid} returns the product."""
    response = await shop_client.get(f"/api/v1/shop/products/{shop_product.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(shop_product.id)
    assert data["name"] == shop_product.name


@pytest.mark.anyio
async def test_get_product_by_slug(shop_client: AsyncClient, shop_product: Product):
    """GET /shop/products/{seo_slug} returns the product."""
    response = await shop_client.get("/api/v1/shop/products/frost-the-ice-dragon")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(shop_product.id)
    assert data["name"] == shop_product.name


@pytest.mark.anyio
async def test_get_product_unknown_slug_returns_404(shop_client: AsyncClient):
    """GET /shop/products/{unknown-slug} returns 404."""
    response = await shop_client.get("/api/v1/shop/products/this-slug-does-not-exist")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_product_unknown_uuid_returns_404(shop_client: AsyncClient):
    """GET /shop/products/{unknown-uuid} returns 404."""
    response = await shop_client.get(f"/api/v1/shop/products/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_product_shop_url_uses_slug_format(
    shop_client: AsyncClient, shop_product: Product
):
    """shop_url must use /products/{slug} canonical format when seo_slug is set."""
    response = await shop_client.get(f"/api/v1/shop/products/{shop_product.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    expected = f"https://www.mystmereforge.co.uk/products/{shop_product.seo_slug}"
    assert (
        data["shop_url"] == expected
    ), f"Expected /products/{{slug}} canonical format, got: {data['shop_url']}"


@pytest.mark.anyio
async def test_list_products_includes_shop_url(
    shop_client: AsyncClient, shop_product: Product, test_tenant: Tenant
):
    """List endpoint must include shop_url with /products/{slug} canonical format."""
    response = await shop_client.get("/api/v1/shop/products")
    assert response.status_code == 200
    products = response.json()["data"]
    assert len(products) >= 1
    matching = [p for p in products if p["id"] == str(shop_product.id)]
    assert matching, "Test product not found in list response"
    product = matching[0]
    expected = f"https://www.mystmereforge.co.uk/products/{shop_product.seo_slug}"
    assert (
        product.get("shop_url") == expected
    ), f"List endpoint shop_url wrong. Expected {expected}, got: {product.get('shop_url')}"


@pytest.mark.anyio
async def test_get_hidden_product_by_slug_returns_404(
    db_session: AsyncSession,
    test_tenant: Tenant,
    sales_channel: SalesChannel,
    shop_client: AsyncClient,
):
    """Products with shop_visible=False are not accessible by slug."""
    hidden = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="HIDDEN-001",
        name="Hidden Product",
        description="Not visible in shop",
        is_active=True,
        shop_visible=False,
        seo_slug="hidden-product",
    )
    db_session.add(hidden)
    await db_session.commit()

    response = await shop_client.get("/api/v1/shop/products/hidden-product")
    assert response.status_code == 404
