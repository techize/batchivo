"""Integration tests for shop designer filtering functionality."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.designer import Designer
from app.models.product import Product
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant
from app.main import app


@pytest_asyncio.fixture
async def shop_designer_artist_a(db_session, test_tenant: Tenant) -> Designer:
    """Create Designer A for shop tests."""
    designer = Designer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Artist Alpha",
        slug="artist-alpha",
        description="First artist",
        is_active=True,
    )
    db_session.add(designer)
    await db_session.commit()
    await db_session.refresh(designer)
    return designer


@pytest_asyncio.fixture
async def shop_designer_artist_b(db_session, test_tenant: Tenant) -> Designer:
    """Create Designer B for shop tests."""
    designer = Designer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Artist Beta",
        slug="artist-beta",
        description="Second artist",
        is_active=True,
    )
    db_session.add(designer)
    await db_session.commit()
    await db_session.refresh(designer)
    return designer


@pytest_asyncio.fixture
async def shop_product_by_artist_a(
    db_session, test_tenant: Tenant, shop_designer_artist_a: Designer
) -> Product:
    """Create a product by Designer A."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        designer_id=shop_designer_artist_a.id,
        sku="ARTIST-A-001",
        name="Product by Artist Alpha",
        description="A product designed by Artist Alpha",
        is_active=True,
        shop_visible=True,
        units_in_stock=5,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_product_by_artist_b(
    db_session, test_tenant: Tenant, shop_designer_artist_b: Designer
) -> Product:
    """Create a product by Designer B."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        designer_id=shop_designer_artist_b.id,
        sku="ARTIST-B-001",
        name="Product by Artist Beta",
        description="A product designed by Artist Beta",
        is_active=True,
        shop_visible=True,
        units_in_stock=10,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_product_no_designer(db_session, test_tenant: Tenant) -> Product:
    """Create a product with no designer."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        designer_id=None,
        sku="NO-DESIGNER-001",
        name="Product Without Designer",
        description="A product with no designer assigned",
        is_active=True,
        shop_visible=True,
        units_in_stock=15,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_sales_channel_designer(
    db_session: AsyncSession, test_tenant: Tenant
) -> SalesChannel:
    """Create a sales channel for shop context."""
    channel = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Designer Shop",
        platform_type="online_shop",
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
async def shop_client_designer(
    db_session: AsyncSession,
    seed_material_types,
    test_tenant: Tenant,
    shop_sales_channel_designer: SalesChannel,
) -> AsyncClient:
    """Create a test HTTP client with ShopContext dependency overridden."""
    from app.auth.dependencies import get_shop_sales_channel, get_shop_tenant
    from app.database import get_db

    async def override_get_db():
        yield db_session

    async def override_get_shop_tenant():
        return test_tenant

    async def override_get_shop_sales_channel():
        return (test_tenant, shop_sales_channel_designer)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shop_tenant] = override_get_shop_tenant
    app.dependency_overrides[get_shop_sales_channel] = override_get_shop_sales_channel

    app.state.limiter.enabled = False

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.state.limiter.enabled = True
    app.dependency_overrides.clear()


class TestShopProductDesignerFilter:
    """Test shop products designer filtering."""

    @pytest.mark.asyncio
    async def test_filter_products_by_designer(
        self,
        shop_client_designer: AsyncClient,
        shop_designer_artist_a: Designer,
        shop_designer_artist_b: Designer,
        shop_product_by_artist_a: Product,
        shop_product_by_artist_b: Product,
    ):
        """Test filtering products by designer slug returns only that designer's products."""
        response = await shop_client_designer.get("/api/v1/shop/products?designer=artist-alpha")
        assert response.status_code == 200
        data = response.json()

        product_skus = [p["sku"] for p in data["data"]]
        assert "ARTIST-A-001" in product_skus
        assert "ARTIST-B-001" not in product_skus

    @pytest.mark.asyncio
    async def test_filter_products_by_different_designer(
        self,
        shop_client_designer: AsyncClient,
        shop_designer_artist_a: Designer,
        shop_designer_artist_b: Designer,
        shop_product_by_artist_a: Product,
        shop_product_by_artist_b: Product,
    ):
        """Test filtering products by different designer slug."""
        response = await shop_client_designer.get("/api/v1/shop/products?designer=artist-beta")
        assert response.status_code == 200
        data = response.json()

        product_skus = [p["sku"] for p in data["data"]]
        assert "ARTIST-B-001" in product_skus
        assert "ARTIST-A-001" not in product_skus

    @pytest.mark.asyncio
    async def test_products_without_designer_filter(
        self,
        shop_client_designer: AsyncClient,
        shop_designer_artist_a: Designer,
        shop_designer_artist_b: Designer,
        shop_product_by_artist_a: Product,
        shop_product_by_artist_b: Product,
        shop_product_no_designer: Product,
    ):
        """Test products without designer filter returns all products."""
        response = await shop_client_designer.get("/api/v1/shop/products")
        assert response.status_code == 200
        data = response.json()

        product_skus = [p["sku"] for p in data["data"]]
        assert "ARTIST-A-001" in product_skus
        assert "ARTIST-B-001" in product_skus
        assert "NO-DESIGNER-001" in product_skus

    @pytest.mark.asyncio
    async def test_filter_nonexistent_designer(
        self,
        shop_client_designer: AsyncClient,
        shop_product_by_artist_a: Product,
    ):
        """Test filtering by non-existent designer slug returns empty list."""
        response = await shop_client_designer.get("/api/v1/shop/products?designer=nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0

    @pytest.mark.asyncio
    async def test_filter_inactive_designer(
        self,
        shop_client_designer: AsyncClient,
        db_session,
        test_tenant: Tenant,
    ):
        """Test filtering by inactive designer returns empty list."""
        # Create inactive designer
        inactive_designer = Designer(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Inactive Artist",
            slug="inactive-artist",
            is_active=False,
        )
        db_session.add(inactive_designer)
        await db_session.commit()

        # Create product by inactive designer
        product = Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            designer_id=inactive_designer.id,
            sku="INACTIVE-001",
            name="Product by Inactive Designer",
            is_active=True,
            shop_visible=True,
            units_in_stock=5,
        )
        db_session.add(product)
        await db_session.commit()

        # Filter should return empty since designer is inactive
        response = await shop_client_designer.get("/api/v1/shop/products?designer=inactive-artist")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 0

    @pytest.mark.asyncio
    async def test_designer_filter_total_count(
        self,
        shop_client_designer: AsyncClient,
        shop_designer_artist_a: Designer,
        shop_designer_artist_b: Designer,
        shop_product_by_artist_a: Product,
        shop_product_by_artist_b: Product,
    ):
        """Test designer filter returns correct total count."""
        response = await shop_client_designer.get("/api/v1/shop/products?designer=artist-alpha")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_designer_filter_pagination(
        self,
        shop_client_designer: AsyncClient,
        shop_designer_artist_a: Designer,
        shop_product_by_artist_a: Product,
        db_session,
        test_tenant: Tenant,
    ):
        """Test designer filter works correctly with pagination."""
        # Create additional products by same designer
        for i in range(5):
            product = Product(
                id=uuid4(),
                tenant_id=test_tenant.id,
                designer_id=shop_designer_artist_a.id,
                sku=f"ARTIST-A-00{i + 2}",
                name=f"Product {i + 2} by Artist Alpha",
                is_active=True,
                shop_visible=True,
                units_in_stock=1,
            )
            db_session.add(product)
        await db_session.commit()

        # Get first page with limit 3
        response = await shop_client_designer.get(
            "/api/v1/shop/products?designer=artist-alpha&page=1&limit=3"
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 3
        assert data["total"] == 6  # 1 from fixture + 5 created here
        assert data["has_more"] is True

        # Get second page
        response = await shop_client_designer.get(
            "/api/v1/shop/products?designer=artist-alpha&page=2&limit=3"
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) == 3
        assert data["total"] == 6
        assert data["has_more"] is False


class TestShopProductDesignerInfo:
    """Test shop product includes designer information."""

    @pytest.mark.asyncio
    async def test_product_includes_designer(
        self,
        shop_client_designer: AsyncClient,
        shop_designer_artist_a: Designer,
        shop_product_by_artist_a: Product,
    ):
        """Test shop product response includes designer info."""
        response = await shop_client_designer.get("/api/v1/shop/products")
        assert response.status_code == 200
        data = response.json()

        product = next((p for p in data["data"] if p["sku"] == "ARTIST-A-001"), None)
        assert product is not None
        assert "designer" in product
        assert product["designer"] is not None
        assert product["designer"]["slug"] == "artist-alpha"
        assert product["designer"]["name"] == "Artist Alpha"

    @pytest.mark.asyncio
    async def test_product_without_designer(
        self,
        shop_client_designer: AsyncClient,
        shop_product_no_designer: Product,
    ):
        """Test product without designer has null designer field."""
        response = await shop_client_designer.get("/api/v1/shop/products")
        assert response.status_code == 200
        data = response.json()

        product = next((p for p in data["data"] if p["sku"] == "NO-DESIGNER-001"), None)
        assert product is not None
        assert product["designer"] is None

    @pytest.mark.asyncio
    async def test_product_detail_includes_designer(
        self,
        shop_client_designer: AsyncClient,
        shop_designer_artist_a: Designer,
        shop_product_by_artist_a: Product,
    ):
        """Test shop product detail includes designer info."""
        response = await shop_client_designer.get(
            f"/api/v1/shop/products/{shop_product_by_artist_a.id}"
        )
        assert response.status_code == 200
        data = response.json()

        product_data = data["data"]
        assert "designer" in product_data
        assert product_data["designer"]["slug"] == "artist-alpha"
        assert product_data["designer"]["name"] == "Artist Alpha"
