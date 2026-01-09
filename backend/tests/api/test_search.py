"""API tests for full-text search functionality."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

pytestmark = pytest.mark.anyio


class TestProductsSearch:
    """Tests for products search API (admin)."""

    @pytest.fixture
    async def search_products(self, db_session, test_tenant):
        """Create products for search testing."""
        from app.models.product import Product

        products = [
            Product(
                tenant_id=test_tenant.id,
                sku="DRAGON-001",
                name="Red Dragon Figurine",
                description="A fierce red dragon with detailed scales",
                is_active=True,
                shop_visible=True,
            ),
            Product(
                tenant_id=test_tenant.id,
                sku="DRAGON-002",
                name="Blue Dragon Figurine",
                description="A majestic blue dragon with wings spread",
                is_active=True,
                shop_visible=True,
            ),
            Product(
                tenant_id=test_tenant.id,
                sku="SQUIRREL-001",
                name="Red Squirrel Set",
                description="Cute woodland creature in resin",
                is_active=True,
                shop_visible=True,
            ),
            Product(
                tenant_id=test_tenant.id,
                sku="INACTIVE-001",
                name="Inactive Dragon Product",
                description="This product is not active",
                is_active=False,
                shop_visible=False,
            ),
        ]

        for product in products:
            db_session.add(product)
        await db_session.commit()

        return products

    async def test_search_products_by_name(
        self, client: AsyncClient, auth_headers, search_products
    ):
        """Search should find products by name."""
        response = await client.get(
            "/api/v1/products",
            params={"search": "Dragon"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        products = data["products"]

        # Should find dragon products
        skus = [p["sku"] for p in products]
        assert "DRAGON-001" in skus
        assert "DRAGON-002" in skus
        # Should not find squirrel
        assert "SQUIRREL-001" not in skus

    async def test_search_products_by_sku(self, client: AsyncClient, auth_headers, search_products):
        """Search should find products by SKU."""
        response = await client.get(
            "/api/v1/products",
            params={"search": "SQUIRREL"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        products = data["products"]

        skus = [p["sku"] for p in products]
        assert "SQUIRREL-001" in skus

    async def test_search_products_by_description(
        self, client: AsyncClient, auth_headers, search_products
    ):
        """Search should find products by description."""
        response = await client.get(
            "/api/v1/products",
            params={"search": "woodland"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        products = data["products"]

        # Should find squirrel (has "woodland" in description)
        skus = [p["sku"] for p in products]
        assert "SQUIRREL-001" in skus

    async def test_search_products_case_insensitive(
        self, client: AsyncClient, auth_headers, search_products
    ):
        """Search should be case insensitive."""
        response = await client.get(
            "/api/v1/products",
            params={"search": "DRAGON"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        response_lower = await client.get(
            "/api/v1/products",
            params={"search": "dragon"},
            headers=auth_headers,
        )

        assert response_lower.status_code == 200
        data_lower = response_lower.json()

        # Both searches should return same results
        assert len(data["products"]) == len(data_lower["products"])

    async def test_search_products_no_results(
        self, client: AsyncClient, auth_headers, search_products
    ):
        """Search with no matches should return empty list."""
        response = await client.get(
            "/api/v1/products",
            params={"search": "nonexistenttermxyz123"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["products"] == []
        assert data["total"] == 0

    async def test_search_products_respects_is_active_filter(
        self, client: AsyncClient, auth_headers, search_products
    ):
        """Search should respect is_active filter."""
        # Search with is_active=True (default)
        response = await client.get(
            "/api/v1/products",
            params={"search": "Dragon"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        skus = [p["sku"] for p in data["products"]]
        # Should not include inactive product
        assert "INACTIVE-001" not in skus

    async def test_search_pagination(self, client: AsyncClient, auth_headers, search_products):
        """Search should support pagination."""
        # Get first page with limit=1
        response = await client.get(
            "/api/v1/products",
            params={"search": "Dragon", "limit": 1, "skip": 0},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) == 1

        # Get second page
        response = await client.get(
            "/api/v1/products",
            params={"search": "Dragon", "limit": 1, "skip": 1},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) == 1

    async def test_list_without_search_returns_all(
        self, client: AsyncClient, auth_headers, search_products
    ):
        """List without search parameter should return all active products."""
        response = await client.get(
            "/api/v1/products",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should include all active products
        skus = [p["sku"] for p in data["products"]]
        assert "DRAGON-001" in skus
        assert "DRAGON-002" in skus
        assert "SQUIRREL-001" in skus


class TestShopSearch:
    """Tests for shop product search (public)."""

    @pytest_asyncio.fixture
    async def shop_sales_channel(self, db_session: AsyncSession, test_tenant: Tenant):
        """Create a sales channel for shop testing."""
        from app.models.sales_channel import SalesChannel

        channel = SalesChannel(
            tenant_id=test_tenant.id,
            name="Test Online Shop",
            platform_type="online_shop",
            is_active=True,
        )
        db_session.add(channel)
        await db_session.commit()
        await db_session.refresh(channel)
        return channel

    @pytest_asyncio.fixture
    async def shop_client(
        self,
        db_session: AsyncSession,
        seed_material_types,
        test_tenant: Tenant,
        shop_sales_channel,
    ):
        """Create a test HTTP client with ShopContext dependency overridden."""
        from app.auth.dependencies import get_shop_sales_channel, get_shop_tenant
        from app.database import get_db
        from app.main import app

        async def override_get_db():
            yield db_session

        async def override_get_shop_tenant():
            return test_tenant

        async def override_get_shop_sales_channel():
            return (test_tenant, shop_sales_channel)

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_shop_tenant] = override_get_shop_tenant
        app.dependency_overrides[get_shop_sales_channel] = override_get_shop_sales_channel

        app.state.limiter.enabled = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

        app.state.limiter.enabled = True
        app.dependency_overrides.clear()

    @pytest_asyncio.fixture
    async def shop_search_products(self, db_session, test_tenant, shop_sales_channel):
        """Create shop products for search testing."""
        from app.models.product import Product
        from app.models.product_pricing import ProductPricing

        products = [
            Product(
                tenant_id=test_tenant.id,
                sku="SHOP-DRAGON-001",
                name="Shop Dragon Red",
                description="A red dragon for the shop",
                is_active=True,
                shop_visible=True,
            ),
            Product(
                tenant_id=test_tenant.id,
                sku="SHOP-DRAGON-002",
                name="Shop Dragon Blue",
                description="A blue dragon for the shop",
                is_active=True,
                shop_visible=True,
            ),
            Product(
                tenant_id=test_tenant.id,
                sku="SHOP-HIDDEN-001",
                name="Hidden Dragon",
                description="This dragon is not visible in shop",
                is_active=True,
                shop_visible=False,
            ),
        ]

        for product in products:
            db_session.add(product)
            await db_session.flush()

            # Add pricing
            pricing = ProductPricing(
                product_id=product.id,
                sales_channel_id=shop_sales_channel.id,
                list_price=19.99,
                is_active=True,
            )
            db_session.add(pricing)

        await db_session.commit()
        return products

    async def test_shop_search_finds_products(self, shop_client: AsyncClient, shop_search_products):
        """Shop search should find visible products."""
        response = await shop_client.get(
            "/api/v1/shop/products",
            params={"search": "Dragon"},
        )

        assert response.status_code == 200
        data = response.json()
        products = data["data"]

        # Should find shop-visible dragon products
        skus = [p["sku"] for p in products]
        assert "SHOP-DRAGON-001" in skus
        assert "SHOP-DRAGON-002" in skus
        # Should not find hidden product
        assert "SHOP-HIDDEN-001" not in skus

    async def test_shop_search_only_shows_visible(
        self, shop_client: AsyncClient, shop_search_products
    ):
        """Shop search should only return shop_visible products."""
        response = await shop_client.get(
            "/api/v1/shop/products",
            params={"search": "Hidden"},
        )

        assert response.status_code == 200
        data = response.json()
        products = data["data"]

        # Should not find the hidden product even when searching for it
        skus = [p["sku"] for p in products]
        assert "SHOP-HIDDEN-001" not in skus

    async def test_shop_search_no_results(self, shop_client: AsyncClient, shop_search_products):
        """Shop search with no matches should return empty."""
        response = await shop_client.get(
            "/api/v1/shop/products",
            params={"search": "nonexistentxyz123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0

    async def test_shop_search_pagination(self, shop_client: AsyncClient, shop_search_products):
        """Shop search should support pagination."""
        response = await shop_client.get(
            "/api/v1/shop/products",
            params={"search": "Dragon", "page": 1, "limit": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["has_more"] is True

    async def test_shop_list_without_search(self, shop_client: AsyncClient, shop_search_products):
        """Shop list without search should return all visible products."""
        response = await shop_client.get("/api/v1/shop/products")

        assert response.status_code == 200
        data = response.json()
        products = data["data"]

        # Should include shop-visible products
        skus = [p["sku"] for p in products]
        assert "SHOP-DRAGON-001" in skus
        assert "SHOP-DRAGON-002" in skus
        # Should not include hidden product
        assert "SHOP-HIDDEN-001" not in skus
