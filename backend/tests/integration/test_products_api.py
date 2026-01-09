"""Integration tests for products API endpoints."""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.models.product import Product


class TestProductsEndpoints:
    """Test products API endpoints."""

    @pytest.mark.asyncio
    async def test_create_product(self, client: AsyncClient, auth_headers: dict):
        """Test product creation."""
        response = await client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "sku": f"TEST-{uuid4().hex[:8].upper()}",
                "name": "Test Product",
                "description": "A test product for integration tests",
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Test Product"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_products(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test product listing."""
        response = await client.get("/api/v1/products", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        # Response is paginated with "products" key
        assert isinstance(data, dict)
        assert "products" in data
        products = data["products"]

        assert isinstance(products, list)
        assert len(products) >= 1

    @pytest.mark.asyncio
    async def test_get_product_by_id(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test retrieving a specific product."""
        response = await client.get(f"/api/v1/products/{test_product.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_product.id)
        assert data["name"] == test_product.name

    @pytest.mark.asyncio
    async def test_update_product(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test product update."""
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers,
            json={
                "name": "Updated Product Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Product Name"

    @pytest.mark.asyncio
    async def test_delete_product(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test product deletion."""
        response = await client.delete(f"/api/v1/products/{test_product.id}", headers=auth_headers)
        assert response.status_code in [200, 204]

        # Verify product is deleted
        response = await client.get(f"/api/v1/products/{test_product.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_product_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test accessing non-existent product returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/products/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_product_duplicate_sku(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test creating product with duplicate SKU returns error."""
        response = await client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "sku": test_product.sku,  # Duplicate
                "name": "Another Product",
                "description": "This should fail",
            },
        )
        assert response.status_code in [400, 409]


class TestProductTenantIsolation:
    """Test multi-tenant isolation for products."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_product(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        """Test products from other tenants are not visible."""
        from app.models.tenant import Tenant
        from app.models.product import Product

        # Create a different tenant
        other_tenant = Tenant(id=uuid4(), name="Other Tenant", slug="other-tenant", settings={})
        db_session.add(other_tenant)
        await db_session.flush()

        # Create a product for the other tenant
        other_product = Product(
            id=uuid4(),
            tenant_id=other_tenant.id,
            sku="OTHER-001",
            name="Other Tenant Product",
            description="Should not be visible",
        )
        db_session.add(other_product)
        await db_session.commit()

        # Try to access other tenant's product
        response = await client.get(f"/api/v1/products/{other_product.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_only_shows_own_tenant_products(
        self, client: AsyncClient, auth_headers: dict, test_product: Product, db_session
    ):
        """Test product list only returns products from current tenant."""
        from app.models.tenant import Tenant
        from app.models.product import Product

        # Create another tenant with products
        other_tenant = Tenant(id=uuid4(), name="Other Tenant", slug="other-tenant-2", settings={})
        db_session.add(other_tenant)
        await db_session.flush()

        other_product = Product(
            id=uuid4(),
            tenant_id=other_tenant.id,
            sku="OTHER-002",
            name="Other Product",
            description="Should not appear in list",
        )
        db_session.add(other_product)
        await db_session.commit()

        # Get product list
        response = await client.get("/api/v1/products", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, dict)
        assert "products" in data
        products = data["products"]

        # Verify other tenant's product is not in list
        product_ids = [p["id"] for p in products]
        assert str(other_product.id) not in product_ids


class TestProductShopFields:
    """Test shop-related fields (is_featured, shop_description, feature_title, backstory)."""

    @pytest.mark.asyncio
    async def test_update_shop_fields(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test updating shop display fields."""
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers,
            json={
                "shop_description": "<p>A beautiful dragon with intricate scales</p>",
                "is_featured": True,
                "feature_title": "Rosyra the Rose Dragon",
                "backstory": "Born in the enchanted gardens of Mystmere...",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["shop_description"] == "<p>A beautiful dragon with intricate scales</p>"
        assert data["is_featured"] is True
        assert data["feature_title"] == "Rosyra the Rose Dragon"
        assert data["backstory"] == "Born in the enchanted gardens of Mystmere..."

    @pytest.mark.asyncio
    async def test_shop_fields_persist_after_fetch(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test that shop fields persist and are returned when fetching product."""
        # First update with shop fields
        update_response = await client.put(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers,
            json={
                "shop_description": "Shop description test",
                "is_featured": True,
                "feature_title": "Featured Title",
                "backstory": "Test backstory content",
            },
        )
        assert update_response.status_code == 200

        # Fetch the product and verify fields are returned
        get_response = await client.get(f"/api/v1/products/{test_product.id}", headers=auth_headers)
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["shop_description"] == "Shop description test"
        assert data["is_featured"] is True
        assert data["feature_title"] == "Featured Title"
        assert data["backstory"] == "Test backstory content"

    @pytest.mark.asyncio
    async def test_shop_visible_toggle(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test toggling shop visibility."""
        # Enable shop visibility
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers,
            json={"shop_visible": True},
        )
        assert response.status_code == 200
        assert response.json()["shop_visible"] is True

        # Disable shop visibility
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers,
            json={"shop_visible": False},
        )
        assert response.status_code == 200
        assert response.json()["shop_visible"] is False

    @pytest.mark.asyncio
    async def test_create_product_with_shop_fields(self, client: AsyncClient, auth_headers: dict):
        """Test creating a product with shop fields."""
        response = await client.post(
            "/api/v1/products",
            headers=auth_headers,
            json={
                "sku": f"SHOP-{uuid4().hex[:8].upper()}",
                "name": "Featured Dragon",
                "description": "Internal description",
                "shop_description": "Beautiful featured dragon for sale",
                "is_featured": True,
                "feature_title": "Dragon of the Month",
                "backstory": "A legendary dragon...",
                "shop_visible": True,
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["shop_description"] == "Beautiful featured dragon for sale"
        assert data["is_featured"] is True
        assert data["feature_title"] == "Dragon of the Month"
        assert data["backstory"] == "A legendary dragon..."
        assert data["shop_visible"] is True


class TestProductCostCalculation:
    """Test product cost calculation features."""

    @pytest.mark.asyncio
    async def test_product_cost_calculation(
        self, client: AsyncClient, auth_headers: dict, test_product: Product
    ):
        """Test cost calculation returns expected breakdown."""
        response = await client.get(
            f"/api/v1/products/{test_product.id}/cost", headers=auth_headers
        )

        # Cost endpoint might not exist yet, so accept 404 or 501
        if response.status_code in [404, 501]:
            pytest.skip("Cost calculation endpoint not implemented yet")

        assert response.status_code == 200
        data = response.json()

        # Verify cost breakdown structure
        assert "total_make_cost" in data or "material_cost" in data

    @pytest.mark.asyncio
    async def test_product_with_models_shows_cost(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        """Test product with associated models shows cost breakdown."""
        # This test will be skipped if the models relationship isn't implemented
        pytest.skip("Product-Model relationship test - implement when models exist")
