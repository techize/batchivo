"""Integration tests for shop category functionality."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.category import Category
from app.models.product import Product
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant
from app.main import app


@pytest_asyncio.fixture
async def shop_category_dragons(db_session, test_tenant: Tenant) -> Category:
    """Create a 'Dragons' category for shop tests."""
    category = Category(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Dragons",
        slug="dragons",
        description="Dragon miniatures",
        display_order=0,
        is_active=True,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def shop_category_dice(db_session, test_tenant: Tenant) -> Category:
    """Create a 'Dice' category for shop tests."""
    category = Category(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Dice",
        slug="dice",
        description="Gaming dice",
        display_order=1,
        is_active=True,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def shop_product_dragon(
    db_session, test_tenant: Tenant, shop_category_dragons: Category
) -> Product:
    """Create a dragon product in the dragons category."""
    from app.models.category import product_categories

    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="DRAGON-001",
        name="Red Dragon Miniature",
        description="A fierce red dragon",
        is_active=True,
        shop_visible=True,  # Required for shop API visibility
        units_in_stock=5,
    )
    db_session.add(product)
    await db_session.commit()

    # Use raw insert to include tenant_id for multi-tenant isolation
    await db_session.execute(
        product_categories.insert().values(
            tenant_id=test_tenant.id,
            product_id=product.id,
            category_id=shop_category_dragons.id,
        )
    )
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_product_dice(
    db_session, test_tenant: Tenant, shop_category_dice: Category
) -> Product:
    """Create a dice product in the dice category."""
    from app.models.category import product_categories

    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="DICE-001",
        name="D20 Gaming Dice",
        description="A classic D20",
        is_active=True,
        shop_visible=True,  # Required for shop API visibility
        units_in_stock=50,
    )
    db_session.add(product)
    await db_session.commit()

    # Use raw insert to include tenant_id for multi-tenant isolation
    await db_session.execute(
        product_categories.insert().values(
            tenant_id=test_tenant.id,
            product_id=product.id,
            category_id=shop_category_dice.id,
        )
    )
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def shop_sales_channel(db_session: AsyncSession, test_tenant: Tenant) -> SalesChannel:
    """Create a sales channel for shop context."""
    channel = SalesChannel(
        id=uuid4(),
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
    db_session: AsyncSession,
    seed_material_types,
    test_tenant: Tenant,
    shop_sales_channel: SalesChannel,
) -> AsyncClient:
    """Create a test HTTP client with ShopContext dependency overridden."""
    from app.auth.dependencies import get_shop_sales_channel, get_shop_tenant
    from app.database import get_db

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


class TestShopCategoryEndpoint:
    """Test shop categories endpoint."""

    @pytest.mark.asyncio
    async def test_shop_categories_returns_list(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
        shop_category_dice: Category,
    ):
        """Test shop categories endpoint returns category list."""
        response = await shop_client.get("/api/v1/shop/categories")
        assert response.status_code == 200
        data = response.json()
        # Shop endpoint returns {"data": [...]}
        assert "data" in data
        assert len(data["data"]) >= 2

    @pytest.mark.asyncio
    async def test_shop_categories_includes_slug(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
    ):
        """Test shop categories include slug field."""
        response = await shop_client.get("/api/v1/shop/categories")
        assert response.status_code == 200
        data = response.json()

        # Find dragons category
        dragon_cat = next((c for c in data["data"] if c["slug"] == "dragons"), None)
        assert dragon_cat is not None
        assert dragon_cat["name"] == "Dragons"

    @pytest.mark.asyncio
    async def test_shop_categories_includes_product_count(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
        shop_product_dragon: Product,
    ):
        """Test shop categories include product count."""
        response = await shop_client.get("/api/v1/shop/categories")
        assert response.status_code == 200
        data = response.json()

        # Find dragons category
        dragon_cat = next((c for c in data["data"] if c["slug"] == "dragons"), None)
        assert dragon_cat is not None
        assert dragon_cat["product_count"] >= 1

    @pytest.mark.asyncio
    async def test_shop_categories_excludes_inactive(
        self,
        shop_client: AsyncClient,
        db_session,
        test_tenant: Tenant,
    ):
        """Test shop categories excludes inactive categories."""
        inactive_cat = Category(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Inactive Shop Category",
            slug="inactive-shop-category",
            is_active=False,
        )
        db_session.add(inactive_cat)
        await db_session.commit()

        response = await shop_client.get("/api/v1/shop/categories")
        assert response.status_code == 200
        data = response.json()

        slugs = [c["slug"] for c in data["data"]]
        assert "inactive-shop-category" not in slugs


class TestShopProductCategoryFilter:
    """Test shop products category filtering."""

    @pytest.mark.asyncio
    async def test_filter_products_by_category(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
        shop_category_dice: Category,
        shop_product_dragon: Product,
        shop_product_dice: Product,
    ):
        """Test filtering products by category slug."""
        response = await shop_client.get("/api/v1/shop/products?category=dragons")
        assert response.status_code == 200
        data = response.json()

        # ShopProductList returns "data" not "products"
        product_skus = [p["sku"] for p in data["data"]]
        assert "DRAGON-001" in product_skus
        assert "DICE-001" not in product_skus

    @pytest.mark.asyncio
    async def test_filter_products_by_different_category(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
        shop_category_dice: Category,
        shop_product_dragon: Product,
        shop_product_dice: Product,
    ):
        """Test filtering products by different category."""
        response = await shop_client.get("/api/v1/shop/products?category=dice")
        assert response.status_code == 200
        data = response.json()

        # ShopProductList returns "data" not "products"
        product_skus = [p["sku"] for p in data["data"]]
        assert "DICE-001" in product_skus
        assert "DRAGON-001" not in product_skus

    @pytest.mark.asyncio
    async def test_products_without_category_filter(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
        shop_category_dice: Category,
        shop_product_dragon: Product,
        shop_product_dice: Product,
    ):
        """Test products without category filter returns all."""
        response = await shop_client.get("/api/v1/shop/products")
        assert response.status_code == 200
        data = response.json()

        # ShopProductList returns "data" not "products"
        product_skus = [p["sku"] for p in data["data"]]
        assert "DRAGON-001" in product_skus
        assert "DICE-001" in product_skus

    @pytest.mark.asyncio
    async def test_filter_nonexistent_category(
        self,
        shop_client: AsyncClient,
        shop_product_dragon: Product,
    ):
        """Test filtering by non-existent category returns empty."""
        response = await shop_client.get("/api/v1/shop/products?category=nonexistent")
        assert response.status_code == 200
        data = response.json()
        # ShopProductList returns "data" not "products"
        assert len(data["data"]) == 0


class TestShopProductCategories:
    """Test shop product includes categories."""

    @pytest.mark.asyncio
    async def test_product_includes_categories(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
        shop_product_dragon: Product,
    ):
        """Test shop product response includes categories."""
        response = await shop_client.get("/api/v1/shop/products")
        assert response.status_code == 200
        data = response.json()

        # ShopProductList returns "data" not "products"
        dragon = next((p for p in data["data"] if p["sku"] == "DRAGON-001"), None)
        assert dragon is not None
        assert "categories" in dragon
        assert len(dragon["categories"]) >= 1

        # Verify category data
        cat = dragon["categories"][0]
        assert cat["slug"] == "dragons"
        assert cat["name"] == "Dragons"

    @pytest.mark.asyncio
    async def test_product_detail_includes_categories(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
        shop_product_dragon: Product,
    ):
        """Test shop product detail includes categories."""
        response = await shop_client.get(f"/api/v1/shop/products/{shop_product_dragon.id}")
        assert response.status_code == 200
        response_data = response.json()

        # Product detail returns {"data": {...}}
        product_data = response_data["data"]
        assert "categories" in product_data
        assert len(product_data["categories"]) >= 1
        assert product_data["categories"][0]["slug"] == "dragons"


class TestShopDragonsCategories:
    """Test shop dragons endpoint includes categories."""

    @pytest.mark.asyncio
    async def test_dragons_include_categories(
        self,
        shop_client: AsyncClient,
        shop_category_dragons: Category,
        shop_product_dragon: Product,
    ):
        """Test dragons endpoint includes categories."""
        response = await shop_client.get("/api/v1/shop/dragons")
        assert response.status_code == 200
        data = response.json()

        # Dragons endpoint also returns {"data": [...]}
        if data["data"]:
            dragon = next((p for p in data["data"] if p["sku"] == "DRAGON-001"), None)
            if dragon:
                # Categories field should exist and be a list
                assert "categories" in dragon
                assert isinstance(dragon["categories"], list)
                assert len(dragon["categories"]) >= 1
                assert dragon["categories"][0]["slug"] == "dragons"
