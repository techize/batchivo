"""Tests for product catalog API endpoints."""

from decimal import Decimal
from uuid import uuid4

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.designer import Designer
from app.models.model import Model
from app.models.product import Product
from app.models.product_component import ProductComponent
from app.models.product_image import ProductImage
from app.models.product_model import ProductModel
from app.models.product_pricing import ProductPricing
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant
from app.models.user import User


# ============================================
# Fixtures
# ============================================


@pytest_asyncio.fixture
async def sales_channel(db_session: AsyncSession, test_tenant: Tenant) -> SalesChannel:
    """Create a test sales channel."""
    channel = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Channel",
        platform_type="online_shop",
        fee_percentage=Decimal("5.0"),
        fee_fixed=Decimal("0.30"),
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture
async def test_designer(db_session: AsyncSession, test_tenant: Tenant) -> Designer:
    """Create a test designer."""
    designer = Designer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Designer",
        slug="test-designer",
        description="A test designer",
        is_active=True,
    )
    db_session.add(designer)
    await db_session.commit()
    await db_session.refresh(designer)
    return designer


@pytest_asyncio.fixture
async def test_model(db_session: AsyncSession, test_tenant: Tenant) -> Model:
    """Create a test 3D model."""
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Dragon Model",
        sku="MDL-TEST-001",
        description="A test 3D model",
        print_time_minutes=120,
        labor_hours=0.5,
        is_active=True,
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture
async def test_product(
    db_session: AsyncSession, test_tenant: Tenant, test_designer: Designer
) -> Product:
    """Create a test product."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="PROD-TEST-001",
        name="Test Dragon Product",
        description="A test product",
        is_active=True,
        shop_visible=True,
        units_in_stock=100,
        designer_id=test_designer.id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def product_with_pricing(
    db_session: AsyncSession,
    test_product: Product,
    sales_channel: SalesChannel,
) -> Product:
    """Create a product with pricing."""
    pricing = ProductPricing(
        id=uuid4(),
        product_id=test_product.id,
        sales_channel_id=sales_channel.id,
        list_price=Decimal("29.99"),
    )
    db_session.add(pricing)
    await db_session.commit()
    await db_session.refresh(test_product)
    return test_product


@pytest_asyncio.fixture
async def product_with_model(
    db_session: AsyncSession,
    test_product: Product,
    test_model: Model,
) -> Product:
    """Create a product with a linked model."""
    product_model = ProductModel(
        id=uuid4(),
        product_id=test_product.id,
        model_id=test_model.id,
        quantity=1,
    )
    db_session.add(product_model)
    await db_session.commit()
    await db_session.refresh(test_product)
    return test_product


@pytest_asyncio.fixture
async def child_product(
    db_session: AsyncSession, test_tenant: Tenant, test_designer: Designer
) -> Product:
    """Create a second product to be used as a child/component."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="PROD-CHILD-001",
        name="Child Component Product",
        description="A child product for bundles",
        is_active=True,
        shop_visible=False,
        units_in_stock=50,
        designer_id=test_designer.id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def product_with_image(
    db_session: AsyncSession,
    test_product: Product,
    test_tenant: Tenant,
) -> tuple[Product, ProductImage]:
    """Create a product with an image."""
    image = ProductImage(
        id=uuid4(),
        tenant_id=test_tenant.id,
        product_id=test_product.id,
        image_url="https://example.com/images/test.jpg",
        alt_text="Test product image",
        display_order=0,
        is_primary=True,
        original_filename="test_image.jpg",
        file_size=1024,
        content_type="image/jpeg",
    )
    db_session.add(image)
    await db_session.commit()
    await db_session.refresh(test_product)
    return test_product, image


# ============================================
# Test Classes
# ============================================


class TestCreateProduct:
    """Tests for product creation."""

    async def test_create_product_success(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Test successful product creation."""
        product_data = {
            "sku": "NEW-PROD-001",
            "name": "New Test Product",
            "description": "A brand new product",
            "is_active": True,
            "shop_visible": False,
            "units_in_stock": 10,
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "NEW-PROD-001"
        assert data["name"] == "New Test Product"
        assert "id" in data

    async def test_create_product_duplicate_sku(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test that duplicate SKU is rejected."""
        product_data = {
            "sku": test_product.sku,  # Use existing SKU
            "name": "Duplicate Product",
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_create_product_with_designer(
        self,
        client: AsyncClient,
        test_designer: Designer,
    ):
        """Test creating product with designer reference."""
        product_data = {
            "sku": "DESIGNER-PROD-001",
            "name": "Designer Product",
            "designer_id": str(test_designer.id),
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["designer_id"] == str(test_designer.id)

    async def test_create_product_invalid_designer(
        self,
        client: AsyncClient,
    ):
        """Test that invalid designer ID is rejected."""
        product_data = {
            "sku": "INVALID-DESIGNER-001",
            "name": "Product with Invalid Designer",
            "designer_id": str(uuid4()),  # Non-existent designer
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 404

    async def test_create_product_with_models(
        self,
        client: AsyncClient,
        test_model: Model,
    ):
        """Test creating product with model associations."""
        product_data = {
            "sku": "MODEL-PROD-001",
            "name": "Product with Models",
            "models": [
                {"model_id": str(test_model.id), "quantity": 2},
            ],
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 201
        data = response.json()
        # Models are created but might not be returned in create response
        # Verify by fetching the product
        product_id = data["id"]
        get_response = await client.get(f"/api/v1/products/{product_id}")
        assert get_response.status_code == 200
        product_data = get_response.json()
        assert len(product_data.get("models", [])) == 1

    async def test_create_product_with_child_products(
        self,
        client: AsyncClient,
        child_product: Product,
    ):
        """Test creating bundle product with child products."""
        product_data = {
            "sku": "BUNDLE-001",
            "name": "Bundle Product",
            "child_products": [
                {"child_product_id": str(child_product.id), "quantity": 1},
            ],
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data.get("child_products", [])) == 1

    async def test_create_product_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        product_data = {
            "sku": "UNAUTH-001",
            "name": "Unauthenticated Product",
        }
        response = await unauthenticated_client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 401


class TestListProducts:
    """Tests for listing products."""

    async def test_list_products_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing with no products."""
        response = await client.get("/api/v1/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "total" in data
        assert data["total"] >= 0

    async def test_list_products_with_data(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test listing with existing products."""
        response = await client.get("/api/v1/products")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        products = data["products"]
        skus = [p["sku"] for p in products]
        assert test_product.sku in skus

    async def test_list_products_pagination(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test pagination parameters."""
        response = await client.get("/api/v1/products?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert data["skip"] == 0
        assert data["limit"] == 10

    async def test_list_products_search(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test search functionality."""
        response = await client.get(f"/api/v1/products?search={test_product.name}")
        assert response.status_code == 200
        data = response.json()
        # Search should find matching product
        skus = [p["sku"] for p in data["products"]]
        assert test_product.sku in skus

    async def test_list_products_active_only(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test filtering by active status."""
        response = await client.get("/api/v1/products?is_active=true")
        assert response.status_code == 200
        data = response.json()
        for product in data["products"]:
            assert product["is_active"] is True

    async def test_list_products_by_designer(
        self,
        client: AsyncClient,
        test_product: Product,
        test_designer: Designer,
    ):
        """Test filtering by designer."""
        response = await client.get(f"/api/v1/products?designer_id={test_designer.id}")
        assert response.status_code == 200
        data = response.json()
        for product in data["products"]:
            assert product.get("designer_id") == str(test_designer.id)

    async def test_list_products_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated listing is rejected."""
        response = await unauthenticated_client.get("/api/v1/products")
        assert response.status_code == 401


class TestGetProduct:
    """Tests for getting single product."""

    async def test_get_product_success(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test successful product retrieval."""
        response = await client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_product.id)
        assert data["sku"] == test_product.sku
        assert data["name"] == test_product.name
        assert "cost_breakdown" in data

    async def test_get_product_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting non-existent product."""
        response = await client.get(f"/api/v1/products/{uuid4()}")
        assert response.status_code == 404

    async def test_get_product_with_cost_breakdown(
        self,
        client: AsyncClient,
        product_with_model: Product,
    ):
        """Test that cost breakdown is included."""
        response = await client.get(f"/api/v1/products/{product_with_model.id}")
        assert response.status_code == 200
        data = response.json()
        assert "cost_breakdown" in data
        cost = data["cost_breakdown"]
        assert "models_cost" in cost
        assert "total_make_cost" in cost

    async def test_get_product_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_product: Product,
    ):
        """Test that unauthenticated retrieval is rejected."""
        response = await unauthenticated_client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 401


class TestUpdateProduct:
    """Tests for updating products."""

    async def test_update_product_success(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test successful product update."""
        update_data = {
            "name": "Updated Product Name",
            "description": "Updated description",
        }
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json=update_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Product Name"
        assert data["description"] == "Updated description"

    async def test_update_product_not_found(
        self,
        client: AsyncClient,
    ):
        """Test updating non-existent product."""
        update_data = {"name": "Ghost Product"}
        response = await client.put(
            f"/api/v1/products/{uuid4()}",
            json=update_data,
        )
        assert response.status_code == 404

    async def test_update_product_stock(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test updating stock quantity."""
        update_data = {"units_in_stock": 200}
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json=update_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["units_in_stock"] == 200

    async def test_update_product_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_product: Product,
    ):
        """Test that unauthenticated updates are rejected."""
        update_data = {"name": "Unauthorized Update"}
        response = await unauthenticated_client.put(
            f"/api/v1/products/{test_product.id}",
            json=update_data,
        )
        assert response.status_code == 401


class TestDeleteProduct:
    """Tests for deleting products."""

    async def test_delete_product_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_designer: Designer,
    ):
        """Test successful product deletion."""
        # Create a product to delete
        product = Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="DELETE-ME-001",
            name="Product to Delete",
            designer_id=test_designer.id,
        )
        db_session.add(product)
        await db_session.commit()

        response = await client.delete(f"/api/v1/products/{product.id}")
        assert response.status_code == 204

    async def test_delete_product_not_found(
        self,
        client: AsyncClient,
    ):
        """Test deleting non-existent product."""
        response = await client.delete(f"/api/v1/products/{uuid4()}")
        assert response.status_code == 404

    async def test_delete_product_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
        test_product: Product,
    ):
        """Test that unauthenticated deletion is rejected."""
        response = await unauthenticated_client.delete(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 401


class TestProductModels:
    """Tests for product-model associations."""

    async def test_add_model_to_product(
        self,
        client: AsyncClient,
        test_product: Product,
        test_model: Model,
    ):
        """Test adding a model to a product."""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/models",
            json={"model_id": str(test_model.id), "quantity": 2},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["model_id"] == str(test_model.id)
        assert data["quantity"] == 2

    async def test_add_model_invalid_model_id(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test adding non-existent model."""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/models",
            json={"model_id": str(uuid4()), "quantity": 1},
        )
        assert response.status_code == 404

    async def test_add_model_product_not_found(
        self,
        client: AsyncClient,
        test_model: Model,
    ):
        """Test adding model to non-existent product."""
        response = await client.post(
            f"/api/v1/products/{uuid4()}/models",
            json={"model_id": str(test_model.id), "quantity": 1},
        )
        assert response.status_code == 404

    async def test_update_product_model(
        self,
        client: AsyncClient,
        product_with_model: Product,
        test_model: Model,
        db_session: AsyncSession,
    ):
        """Test updating model quantity in product."""
        # Get the product_model ID
        from sqlalchemy import select

        result = await db_session.execute(
            select(ProductModel).where(
                ProductModel.product_id == product_with_model.id,
                ProductModel.model_id == test_model.id,
            )
        )
        pm = result.scalar_one()

        response = await client.put(
            f"/api/v1/products/{product_with_model.id}/models/{pm.id}",
            json={"model_id": str(test_model.id), "quantity": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 5

    async def test_delete_product_model(
        self,
        client: AsyncClient,
        product_with_model: Product,
        test_model: Model,
        db_session: AsyncSession,
    ):
        """Test removing model from product."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(ProductModel).where(
                ProductModel.product_id == product_with_model.id,
                ProductModel.model_id == test_model.id,
            )
        )
        pm = result.scalar_one()

        response = await client.delete(f"/api/v1/products/{product_with_model.id}/models/{pm.id}")
        assert response.status_code == 204


class TestProductPricing:
    """Tests for product pricing."""

    async def test_add_pricing_to_product(
        self,
        client: AsyncClient,
        test_product: Product,
        sales_channel: SalesChannel,
    ):
        """Test adding pricing to a product."""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/pricing",
            json={
                "sales_channel_id": str(sales_channel.id),
                "list_price": 29.99,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sales_channel_id"] == str(sales_channel.id)
        assert float(data["list_price"]) == 29.99

    async def test_add_pricing_invalid_channel(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test adding pricing with invalid channel."""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/pricing",
            json={
                "sales_channel_id": str(uuid4()),
                "list_price": 19.99,
            },
        )
        assert response.status_code == 404

    async def test_add_pricing_product_not_found(
        self,
        client: AsyncClient,
        sales_channel: SalesChannel,
    ):
        """Test adding pricing to non-existent product."""
        response = await client.post(
            f"/api/v1/products/{uuid4()}/pricing",
            json={
                "sales_channel_id": str(sales_channel.id),
                "list_price": 19.99,
            },
        )
        assert response.status_code == 404

    async def test_update_pricing(
        self,
        client: AsyncClient,
        product_with_pricing: Product,
        db_session: AsyncSession,
    ):
        """Test updating product pricing."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(ProductPricing).where(ProductPricing.product_id == product_with_pricing.id)
        )
        pricing = result.scalar_one()

        response = await client.put(
            f"/api/v1/products/{product_with_pricing.id}/pricing/{pricing.id}",
            json={"list_price": 39.99},
        )
        assert response.status_code == 200
        data = response.json()
        assert float(data["list_price"]) == 39.99

    async def test_delete_pricing(
        self,
        client: AsyncClient,
        product_with_pricing: Product,
        db_session: AsyncSession,
    ):
        """Test removing pricing from product."""
        from sqlalchemy import select

        result = await db_session.execute(
            select(ProductPricing).where(ProductPricing.product_id == product_with_pricing.id)
        )
        pricing = result.scalar_one()

        response = await client.delete(
            f"/api/v1/products/{product_with_pricing.id}/pricing/{pricing.id}"
        )
        assert response.status_code == 204


class TestProductComponents:
    """Tests for product components (child products in bundles)."""

    async def test_add_child_product(
        self,
        client: AsyncClient,
        test_product: Product,
        child_product: Product,
    ):
        """Test adding a child product to create a bundle."""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/components",
            json={"child_product_id": str(child_product.id), "quantity": 2},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["child_product_id"] == str(child_product.id)
        assert data["quantity"] == 2

    async def test_add_child_product_invalid(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test adding non-existent child product."""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/components",
            json={"child_product_id": str(uuid4()), "quantity": 1},
        )
        assert response.status_code == 404

    async def test_add_child_product_self_reference(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test that product cannot be its own child."""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/components",
            json={"child_product_id": str(test_product.id), "quantity": 1},
        )
        assert response.status_code == 400

    async def test_update_component(
        self,
        client: AsyncClient,
        test_product: Product,
        child_product: Product,
        db_session: AsyncSession,
    ):
        """Test updating component quantity."""
        # First add the component
        component = ProductComponent(
            id=uuid4(),
            parent_product_id=test_product.id,
            child_product_id=child_product.id,
            quantity=1,
        )
        db_session.add(component)
        await db_session.commit()

        response = await client.put(
            f"/api/v1/products/{test_product.id}/components/{component.id}",
            json={"quantity": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 5

    async def test_delete_component(
        self,
        client: AsyncClient,
        test_product: Product,
        child_product: Product,
        db_session: AsyncSession,
    ):
        """Test removing child product from bundle."""
        component = ProductComponent(
            id=uuid4(),
            parent_product_id=test_product.id,
            child_product_id=child_product.id,
            quantity=1,
        )
        db_session.add(component)
        await db_session.commit()

        response = await client.delete(
            f"/api/v1/products/{test_product.id}/components/{component.id}"
        )
        assert response.status_code == 204


class TestProductImages:
    """Tests for product images."""

    async def test_list_product_images_empty(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test listing images for product with no images."""
        response = await client.get(f"/api/v1/products/{test_product.id}/images")
        assert response.status_code == 200
        data = response.json()
        # Response is wrapped in an object with images and total
        assert "images" in data
        assert data["images"] == []
        assert data["total"] == 0

    async def test_list_product_images_with_data(
        self,
        client: AsyncClient,
        product_with_image: tuple[Product, ProductImage],
    ):
        """Test listing images for product with images."""
        product, image = product_with_image
        response = await client.get(f"/api/v1/products/{product.id}/images")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_list_images_product_not_found(
        self,
        client: AsyncClient,
    ):
        """Test listing images for non-existent product."""
        response = await client.get(f"/api/v1/products/{uuid4()}/images")
        assert response.status_code == 404

    async def test_update_image_metadata(
        self,
        client: AsyncClient,
        product_with_image: tuple[Product, ProductImage],
    ):
        """Test updating image metadata."""
        product, image = product_with_image
        response = await client.patch(
            f"/api/v1/products/{product.id}/images/{image.id}",
            json={"alt_text": "New alt text", "display_order": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["alt_text"] == "New alt text"

    async def test_set_primary_image(
        self,
        client: AsyncClient,
        product_with_image: tuple[Product, ProductImage],
    ):
        """Test setting an image as primary."""
        product, image = product_with_image
        response = await client.post(f"/api/v1/products/{product.id}/images/{image.id}/set-primary")
        assert response.status_code == 200
        data = response.json()
        assert data["is_primary"] is True

    async def test_delete_image(
        self,
        client: AsyncClient,
        product_with_image: tuple[Product, ProductImage],
    ):
        """Test deleting a product image."""
        product, image = product_with_image
        response = await client.delete(f"/api/v1/products/{product.id}/images/{image.id}")
        assert response.status_code == 204

    async def test_delete_image_not_found(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test deleting non-existent image."""
        response = await client.delete(f"/api/v1/products/{test_product.id}/images/{uuid4()}")
        assert response.status_code == 404


class TestProductEdgeCases:
    """Tests for edge cases and validation."""

    async def test_create_product_minimal_fields(
        self,
        client: AsyncClient,
    ):
        """Test creating product with only required fields."""
        product_data = {
            "sku": "MINIMAL-001",
            "name": "Minimal Product",
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == "MINIMAL-001"
        # Check defaults
        assert data["is_active"] is True
        assert data["shop_visible"] is False

    async def test_update_product_partial(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test partial product update."""
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json={"shop_visible": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["shop_visible"] is True
        # Original fields unchanged
        assert data["name"] == test_product.name

    async def test_product_with_zero_stock(
        self,
        client: AsyncClient,
        test_product: Product,
    ):
        """Test updating product to zero stock."""
        response = await client.put(
            f"/api/v1/products/{test_product.id}",
            json={"units_in_stock": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["units_in_stock"] == 0

    async def test_product_decimal_pricing(
        self,
        client: AsyncClient,
        test_product: Product,
        sales_channel: SalesChannel,
    ):
        """Test pricing with decimal values."""
        response = await client.post(
            f"/api/v1/products/{test_product.id}/pricing",
            json={
                "sales_channel_id": str(sales_channel.id),
                "list_price": 19.99,
            },
        )
        assert response.status_code == 201
        data = response.json()
        # Check decimal precision is maintained
        assert float(data["list_price"]) == 19.99

    async def test_create_product_long_description(
        self,
        client: AsyncClient,
    ):
        """Test creating product with long description."""
        long_desc = "A" * 5000  # 5000 character description
        product_data = {
            "sku": "LONGDESC-001",
            "name": "Long Description Product",
            "description": long_desc,
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["description"]) == 5000

    async def test_create_product_special_characters_in_name(
        self,
        client: AsyncClient,
    ):
        """Test creating product with special characters."""
        product_data = {
            "sku": "SPECIAL-001",
            "name": "Dragon's Lair - Limited Edition (2024)",
            "description": "Features special chars",
        }
        response = await client.post(
            "/api/v1/products",
            json=product_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Dragon's Lair - Limited Edition (2024)"
