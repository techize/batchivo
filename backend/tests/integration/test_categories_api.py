"""Integration tests for categories API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4

from app.models.category import Category
from app.models.product import Product
from app.models.tenant import Tenant


@pytest_asyncio.fixture
async def test_category(db_session, test_tenant: Tenant) -> Category:
    """Create a test category."""
    category = Category(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Category",
        slug="test-category",
        description="A test category",
        display_order=0,
        is_active=True,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest_asyncio.fixture
async def test_category_with_product(
    db_session, test_tenant: Tenant, test_product: Product
) -> Category:
    """Create a test category with a product assigned."""
    from app.models.category import product_categories

    category = Category(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Category With Product",
        slug="category-with-product",
        description="A category with a product",
        display_order=0,
        is_active=True,
    )
    db_session.add(category)
    await db_session.commit()

    # Use raw insert to include tenant_id for multi-tenant isolation
    await db_session.execute(
        product_categories.insert().values(
            tenant_id=test_tenant.id,
            product_id=test_product.id,
            category_id=category.id,
        )
    )
    await db_session.commit()
    await db_session.refresh(category)
    return category


class TestCategoryCRUD:
    """Test category CRUD API endpoints."""

    @pytest.mark.asyncio
    async def test_create_category(self, client: AsyncClient, auth_headers: dict):
        """Test category creation."""
        response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "New Category",
                "description": "A new test category",
                "display_order": 1,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Category"
        assert data["slug"] == "new-category"
        assert data["description"] == "A new test category"
        assert data["display_order"] == 1
        assert data["is_active"] is True
        assert data["product_count"] == 0
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_category_auto_slug(self, client: AsyncClient, auth_headers: dict):
        """Test category creation auto-generates slug from name."""
        response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "My Special Category!",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "my-special-category"

    @pytest.mark.asyncio
    async def test_create_category_custom_slug(self, client: AsyncClient, auth_headers: dict):
        """Test category creation with custom slug."""
        response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Custom Slug Category",
                "slug": "my-custom-slug",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "my-custom-slug"

    @pytest.mark.asyncio
    async def test_create_category_duplicate_slug(
        self, client: AsyncClient, auth_headers: dict, test_category: Category
    ):
        """Test creating category with duplicate slug fails."""
        response = await client.post(
            "/api/v1/categories",
            headers=auth_headers,
            json={
                "name": "Another Category",
                "slug": test_category.slug,  # Duplicate
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_categories(
        self, client: AsyncClient, auth_headers: dict, test_category: Category
    ):
        """Test listing categories."""
        response = await client.get("/api/v1/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "total" in data
        assert len(data["categories"]) >= 1

    @pytest.mark.asyncio
    async def test_list_categories_excludes_inactive(
        self, client: AsyncClient, auth_headers: dict, db_session, test_tenant: Tenant
    ):
        """Test listing categories excludes inactive by default."""
        # Create an inactive category
        inactive_cat = Category(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Inactive Category",
            slug="inactive-category",
            is_active=False,
        )
        db_session.add(inactive_cat)
        await db_session.commit()

        response = await client.get("/api/v1/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        slugs = [c["slug"] for c in data["categories"]]
        assert "inactive-category" not in slugs

    @pytest.mark.asyncio
    async def test_list_categories_include_inactive(
        self, client: AsyncClient, auth_headers: dict, db_session, test_tenant: Tenant
    ):
        """Test listing categories can include inactive."""
        inactive_cat = Category(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Inactive Category 2",
            slug="inactive-category-2",
            is_active=False,
        )
        db_session.add(inactive_cat)
        await db_session.commit()

        response = await client.get(
            "/api/v1/categories?include_inactive=true", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        slugs = [c["slug"] for c in data["categories"]]
        assert "inactive-category-2" in slugs

    @pytest.mark.asyncio
    async def test_list_categories_search(
        self, client: AsyncClient, auth_headers: dict, test_category: Category
    ):
        """Test listing categories with search filter."""
        response = await client.get(
            f"/api/v1/categories?search={test_category.name[:4]}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["categories"]) >= 1
        assert any(c["id"] == str(test_category.id) for c in data["categories"])

    @pytest.mark.asyncio
    async def test_get_category(
        self, client: AsyncClient, auth_headers: dict, test_category: Category
    ):
        """Test getting a single category."""
        response = await client.get(f"/api/v1/categories/{test_category.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_category.id)
        assert data["name"] == test_category.name
        assert data["slug"] == test_category.slug

    @pytest.mark.asyncio
    async def test_get_category_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent category returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/categories/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_category(
        self, client: AsyncClient, auth_headers: dict, test_category: Category
    ):
        """Test updating a category."""
        response = await client.patch(
            f"/api/v1/categories/{test_category.id}",
            headers=auth_headers,
            json={
                "name": "Updated Category Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Category Name"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_category_slug(
        self, client: AsyncClient, auth_headers: dict, test_category: Category
    ):
        """Test updating category slug."""
        response = await client.patch(
            f"/api/v1/categories/{test_category.id}",
            headers=auth_headers,
            json={"slug": "updated-slug"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "updated-slug"

    @pytest.mark.asyncio
    async def test_update_category_duplicate_slug_fails(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_category: Category,
        db_session,
        test_tenant: Tenant,
    ):
        """Test updating category to duplicate slug fails."""
        # Create another category
        other_cat = Category(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Other Category",
            slug="other-category",
            is_active=True,
        )
        db_session.add(other_cat)
        await db_session.commit()

        # Try to update test_category to use other_cat's slug
        response = await client.patch(
            f"/api/v1/categories/{test_category.id}",
            headers=auth_headers,
            json={"slug": "other-category"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_category_soft(
        self, client: AsyncClient, auth_headers: dict, test_category: Category
    ):
        """Test soft deleting a category."""
        response = await client.delete(
            f"/api/v1/categories/{test_category.id}", headers=auth_headers
        )
        assert response.status_code == 204

        # Category should still exist but be inactive
        response = await client.get(f"/api/v1/categories/{test_category.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_category_hard(
        self, client: AsyncClient, auth_headers: dict, test_category: Category
    ):
        """Test hard deleting a category."""
        response = await client.delete(
            f"/api/v1/categories/{test_category.id}?hard_delete=true",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Category should be gone
        response = await client.get(f"/api/v1/categories/{test_category.id}", headers=auth_headers)
        assert response.status_code == 404


class TestCategoryProductAssignment:
    """Test category-product assignment endpoints."""

    @pytest.mark.asyncio
    async def test_list_category_products(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_category_with_product: Category,
    ):
        """Test listing products in a category."""
        response = await client.get(
            f"/api/v1/categories/{test_category_with_product.id}/products",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_add_product_to_category(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_category: Category,
        test_product: Product,
    ):
        """Test adding a product to a category."""
        response = await client.post(
            f"/api/v1/categories/{test_category.id}/products/{test_product.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify product is in category
        response = await client.get(
            f"/api/v1/categories/{test_category.id}/products",
            headers=auth_headers,
        )
        data = response.json()
        product_ids = [p["id"] for p in data["products"]]
        assert str(test_product.id) in product_ids

    @pytest.mark.asyncio
    async def test_add_product_to_category_idempotent(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_category_with_product: Category,
        test_product: Product,
    ):
        """Test adding product already in category is idempotent."""
        # Product is already in category via fixture
        response = await client.post(
            f"/api/v1/categories/{test_category_with_product.id}/products/{test_product.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_remove_product_from_category(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_category_with_product: Category,
        test_product: Product,
    ):
        """Test removing a product from a category."""
        response = await client.delete(
            f"/api/v1/categories/{test_category_with_product.id}/products/{test_product.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify product is not in category
        response = await client.get(
            f"/api/v1/categories/{test_category_with_product.id}/products",
            headers=auth_headers,
        )
        data = response.json()
        product_ids = [p["id"] for p in data["products"]]
        assert str(test_product.id) not in product_ids

    @pytest.mark.asyncio
    async def test_add_product_nonexistent_category(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_product: Product,
    ):
        """Test adding product to non-existent category fails."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/categories/{fake_id}/products/{test_product.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_add_nonexistent_product_to_category(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_category: Category,
    ):
        """Test adding non-existent product to category fails."""
        fake_id = uuid4()
        response = await client.post(
            f"/api/v1/categories/{test_category.id}/products/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestCategoryTenantIsolation:
    """Test multi-tenant isolation for categories."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_category(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        """Test categories from other tenants are not visible."""
        # Create a different tenant
        other_tenant = Tenant(id=uuid4(), name="Other Tenant", slug="other-tenant-cat", settings={})
        db_session.add(other_tenant)
        await db_session.flush()

        # Create a category for the other tenant
        other_category = Category(
            id=uuid4(),
            tenant_id=other_tenant.id,
            name="Other Tenant Category",
            slug="other-tenant-cat",
            is_active=True,
        )
        db_session.add(other_category)
        await db_session.commit()

        # Try to access other tenant's category
        response = await client.get(f"/api/v1/categories/{other_category.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_only_shows_own_tenant_categories(
        self, client: AsyncClient, auth_headers: dict, test_category: Category, db_session
    ):
        """Test category list only returns categories from current tenant."""
        # Create another tenant with categories
        other_tenant = Tenant(
            id=uuid4(), name="Other Tenant", slug="other-tenant-cat-2", settings={}
        )
        db_session.add(other_tenant)
        await db_session.flush()

        other_category = Category(
            id=uuid4(),
            tenant_id=other_tenant.id,
            name="Other Category",
            slug="other-category-hidden",
            is_active=True,
        )
        db_session.add(other_category)
        await db_session.commit()

        # Get category list
        response = await client.get("/api/v1/categories", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        category_ids = [c["id"] for c in data["categories"]]
        assert str(other_category.id) not in category_ids


class TestCategoryProductCount:
    """Test category product count calculations."""

    @pytest.mark.asyncio
    async def test_category_shows_product_count(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_category_with_product: Category,
    ):
        """Test category response includes accurate product count."""
        response = await client.get(
            f"/api/v1/categories/{test_category_with_product.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["product_count"] >= 1

    @pytest.mark.asyncio
    async def test_category_list_shows_product_counts(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_category_with_product: Category,
    ):
        """Test category list includes product counts."""
        response = await client.get("/api/v1/categories", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Find our test category
        cat = next(
            (c for c in data["categories"] if c["id"] == str(test_category_with_product.id)),
            None,
        )
        assert cat is not None
        assert cat["product_count"] >= 1
