# Regression test: shop products list total uses COUNT not len(scalars().all()).
from uuid import uuid4
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.product import Product
from app.models.sales_channel import SalesChannel


@pytest_asyncio.fixture
async def ch(db_session, test_tenant):
    sc = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Shop",
        platform_type="online_shop",
        is_active=True,
    )
    db_session.add(sc)
    await db_session.commit()
    await db_session.refresh(sc)
    return sc


@pytest_asyncio.fixture
async def mixed(db_session, test_tenant, ch):
    # 3 visible active, 1 inactive, 1 hidden
    for s in ["VA", "VB", "VC"]:
        db_session.add(
            Product(
                id=uuid4(),
                tenant_id=test_tenant.id,
                sku=s,
                name=s,
                is_active=True,
                shop_visible=True,
            )
        )
    db_session.add(
        Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="INA",
            name="Inactive",
            is_active=False,
            shop_visible=True,
        )
    )
    db_session.add(
        Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="HID",
            name="Hidden",
            is_active=True,
            shop_visible=False,
        )
    )
    await db_session.commit()


@pytest_asyncio.fixture
async def lclient(db_session, test_tenant, ch):
    from app.auth.dependencies import get_shop_sales_channel
    from app.database import get_db

    async def override_db():
        yield db_session

    async def override_ctx():
        return (test_tenant, ch)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_shop_sales_channel] = override_ctx
    app.state.limiter.enabled = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_total_excludes_inactive_and_hidden(lclient, mixed):
    # Regression: total uses COUNT(*) not len(scalars().all()), so inactive/hidden excluded
    resp = await lclient.get("/api/v1/shop/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["data"]) == 3


@pytest.mark.anyio
async def test_total_zero_when_no_products(lclient):
    # total returns 0 not an error when no shop products exist
    resp = await lclient.get("/api/v1/shop/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
