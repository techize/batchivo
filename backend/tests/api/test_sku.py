"""Tests for SKU generation API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consumable import ConsumableType
from app.models.material import MaterialType
from app.models.model import Model
from app.models.product import Product
from app.models.spool import Spool
from app.models.tenant import Tenant


class TestSKUEndpoints:
    """Tests for SKU generation API endpoints."""

    @pytest_asyncio.fixture
    async def product_with_sku(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> Product:
        """Create a product with specific SKU."""
        product = Product(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Test Product",
            sku="PROD-015",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product

    @pytest_asyncio.fixture
    async def model_with_sku(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> Model:
        """Create a model with specific SKU."""
        model = Model(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Test Model",
            sku="MOD-008",
            print_time_minutes=30,
            is_active=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)
        return model

    @pytest_asyncio.fixture
    async def consumable_with_sku(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> ConsumableType:
        """Create a consumable with specific SKU."""
        consumable = ConsumableType(
            id=uuid4(),
            tenant_id=test_tenant.id,
            name="Test Consumable",
            sku="COM-003",
            unit_of_measure="piece",
            quantity_on_hand=10,
            is_active=True,
        )
        db_session.add(consumable)
        await db_session.commit()
        await db_session.refresh(consumable)
        return consumable

    @pytest_asyncio.fixture
    async def spool_with_sku(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_material_type: MaterialType,
    ) -> Spool:
        """Create a spool with specific SKU."""
        spool = Spool(
            id=uuid4(),
            tenant_id=test_tenant.id,
            material_type_id=test_material_type.id,
            spool_id="FIL-022",
            brand="Test Brand",
            color="Red",
            initial_weight=1000.0,
            current_weight=1000.0,
            is_active=True,
        )
        db_session.add(spool)
        await db_session.commit()
        await db_session.refresh(spool)
        return spool

    # =========================================================================
    # Next SKU Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_next_sku_product(
        self,
        client: AsyncClient,
        product_with_sku: Product,
    ):
        """Test getting next SKU for products."""
        response = await client.get("/api/v1/sku/next/PROD")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "PROD"
        assert data["next_sku"] == "PROD-016"  # After PROD-015
        assert data["highest_existing"] == 15

    @pytest.mark.asyncio
    async def test_get_next_sku_model(
        self,
        client: AsyncClient,
        model_with_sku: Model,
    ):
        """Test getting next SKU for models."""
        response = await client.get("/api/v1/sku/next/MOD")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "MOD"
        assert data["next_sku"] == "MOD-009"  # After MOD-008
        assert data["highest_existing"] == 8

    @pytest.mark.asyncio
    async def test_get_next_sku_consumable(
        self,
        client: AsyncClient,
        consumable_with_sku: ConsumableType,
    ):
        """Test getting next SKU for consumables."""
        response = await client.get("/api/v1/sku/next/COM")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "COM"
        assert data["next_sku"] == "COM-004"  # After COM-003
        assert data["highest_existing"] == 3

    @pytest.mark.asyncio
    async def test_get_next_sku_filament(
        self,
        client: AsyncClient,
        spool_with_sku: Spool,
    ):
        """Test getting next SKU for filament spools."""
        response = await client.get("/api/v1/sku/next/FIL")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "FIL"
        assert data["next_sku"] == "FIL-023"  # After FIL-022
        assert data["highest_existing"] == 22

    @pytest.mark.asyncio
    async def test_get_next_sku_empty_database(
        self,
        client: AsyncClient,
    ):
        """Test getting next SKU when no entities exist."""
        response = await client.get("/api/v1/sku/next/PROD")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "PROD"
        assert data["next_sku"] == "PROD-001"  # First SKU
        assert data["highest_existing"] == 0

    @pytest.mark.asyncio
    async def test_get_next_sku_case_insensitive(
        self,
        client: AsyncClient,
        product_with_sku: Product,
    ):
        """Test that entity type is case insensitive."""
        # Test lowercase
        response = await client.get("/api/v1/sku/next/prod")
        assert response.status_code == 200
        assert response.json()["entity_type"] == "PROD"

        # Test mixed case
        response = await client.get("/api/v1/sku/next/Prod")
        assert response.status_code == 200
        assert response.json()["entity_type"] == "PROD"

    @pytest.mark.asyncio
    async def test_get_next_sku_invalid_entity_type(
        self,
        client: AsyncClient,
    ):
        """Test getting next SKU with invalid entity type."""
        response = await client.get("/api/v1/sku/next/INVALID")

        assert response.status_code == 400
        data = response.json()
        assert "invalid" in data["detail"].lower()
        assert "PROD" in data["detail"]  # Should show valid types

    @pytest.mark.asyncio
    async def test_get_next_sku_run_type_not_allowed(
        self,
        client: AsyncClient,
    ):
        """Test that RUN entity type is not allowed via this endpoint."""
        response = await client.get("/api/v1/sku/next/RUN")

        assert response.status_code == 400
        data = response.json()
        assert "production run" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_next_sku_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/sku/next/PROD")
        assert response.status_code == 401

    # =========================================================================
    # Check SKU Availability Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_check_sku_available(
        self,
        client: AsyncClient,
        product_with_sku: Product,
    ):
        """Test checking availability for an unused SKU."""
        response = await client.get("/api/v1/sku/check/PROD/PROD-999")

        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "PROD-999"
        assert data["available"] is True

    @pytest.mark.asyncio
    async def test_check_sku_unavailable(
        self,
        client: AsyncClient,
        product_with_sku: Product,
    ):
        """Test checking availability for a used SKU."""
        response = await client.get("/api/v1/sku/check/PROD/PROD-015")

        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "PROD-015"
        assert data["available"] is False

    @pytest.mark.asyncio
    async def test_check_sku_model(
        self,
        client: AsyncClient,
        model_with_sku: Model,
    ):
        """Test checking SKU availability for models."""
        # Existing SKU
        response = await client.get("/api/v1/sku/check/MOD/MOD-008")
        assert response.status_code == 200
        assert response.json()["available"] is False

        # New SKU
        response = await client.get("/api/v1/sku/check/MOD/MOD-100")
        assert response.status_code == 200
        assert response.json()["available"] is True

    @pytest.mark.asyncio
    async def test_check_sku_consumable(
        self,
        client: AsyncClient,
        consumable_with_sku: ConsumableType,
    ):
        """Test checking SKU availability for consumables."""
        # Existing SKU
        response = await client.get("/api/v1/sku/check/COM/COM-003")
        assert response.status_code == 200
        assert response.json()["available"] is False

        # New SKU
        response = await client.get("/api/v1/sku/check/COM/COM-050")
        assert response.status_code == 200
        assert response.json()["available"] is True

    @pytest.mark.asyncio
    async def test_check_sku_filament(
        self,
        client: AsyncClient,
        spool_with_sku: Spool,
    ):
        """Test checking SKU availability for filament spools."""
        # Existing SKU
        response = await client.get("/api/v1/sku/check/FIL/FIL-022")
        assert response.status_code == 200
        assert response.json()["available"] is False

        # New SKU
        response = await client.get("/api/v1/sku/check/FIL/FIL-001")
        assert response.status_code == 200
        assert response.json()["available"] is True

    @pytest.mark.asyncio
    async def test_check_sku_case_insensitive(
        self,
        client: AsyncClient,
        product_with_sku: Product,
    ):
        """Test that entity type is case insensitive for check."""
        response = await client.get("/api/v1/sku/check/prod/PROD-999")
        assert response.status_code == 200
        assert response.json()["available"] is True

    @pytest.mark.asyncio
    async def test_check_sku_invalid_entity_type(
        self,
        client: AsyncClient,
    ):
        """Test checking SKU with invalid entity type."""
        response = await client.get("/api/v1/sku/check/INVALID/SOME-SKU")

        assert response.status_code == 400
        data = response.json()
        assert "invalid" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_check_sku_run_type_not_allowed(
        self,
        client: AsyncClient,
    ):
        """Test that RUN entity type is not allowed for check."""
        response = await client.get("/api/v1/sku/check/RUN/RUN-001")

        assert response.status_code == 400
        data = response.json()
        assert "production run" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_check_sku_unauthenticated(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test that unauthenticated requests are rejected."""
        response = await unauthenticated_client.get("/api/v1/sku/check/PROD/PROD-001")
        assert response.status_code == 401
