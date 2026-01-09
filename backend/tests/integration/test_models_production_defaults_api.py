"""Integration tests for models production defaults API endpoint."""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model import Model
from app.models.model_material import ModelMaterial
from app.models.spool import Spool
from app.models.material import MaterialType


@pytest_asyncio.fixture(scope="function")
async def test_model_with_single_material_bom(
    db_session: AsyncSession, test_tenant, test_spool: Spool
):
    """Create a test model with single material in BOM."""
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="MODEL-SINGLE-001",
        name="Single Material Model",
        description="Test model with one material",
        machine="Prusa i3 MK3S",
        print_time_minutes=120,
        prints_per_plate=1,
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    # Add BOM material
    model_material = ModelMaterial(
        id=uuid4(),
        model_id=model.id,
        spool_id=test_spool.id,
        weight_grams=Decimal("50.5"),
        cost_per_gram=Decimal("0.025"),
    )
    db_session.add(model_material)

    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture(scope="function")
async def test_model_with_multi_material_bom(
    db_session: AsyncSession, test_tenant, test_material_type: MaterialType
):
    """Create a test model with multiple materials in BOM."""
    # Create model
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="MODEL-MULTI-001",
        name="Multi Material Model",
        description="Test model with multiple materials",
        machine="Prusa XL",
        print_time_minutes=480,
        prints_per_plate=5,
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    # Create multiple spools
    spool_blue = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        spool_id="TEST-BLUE-001",
        brand="eSun",
        color="Blue",
        color_hex="#0000FF",
        initial_weight=Decimal("1000.0"),
        current_weight=Decimal("800.0"),
        purchase_price=Decimal("25.00"),
        is_active=True,
    )
    spool_red = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        spool_id="TEST-RED-001",
        brand="eSun",
        color="Red",
        color_hex="#FF0000",
        initial_weight=Decimal("1000.0"),
        current_weight=Decimal("600.0"),
        purchase_price=Decimal("25.00"),
        is_active=True,
    )
    db_session.add_all([spool_blue, spool_red])
    await db_session.flush()

    # Add BOM materials
    model_materials = [
        ModelMaterial(
            id=uuid4(),
            model_id=model.id,
            spool_id=spool_blue.id,
            weight_grams=Decimal("50.0"),
            cost_per_gram=Decimal("0.025"),
        ),
        ModelMaterial(
            id=uuid4(),
            model_id=model.id,
            spool_id=spool_red.id,
            weight_grams=Decimal("30.0"),
            cost_per_gram=Decimal("0.025"),
        ),
    ]
    db_session.add_all(model_materials)

    await db_session.commit()
    await db_session.refresh(model)
    return model


@pytest_asyncio.fixture(scope="function")
async def test_model_with_inactive_spool_bom(
    db_session: AsyncSession, test_tenant, test_material_type: MaterialType
):
    """Create a test model with inactive spool in BOM."""
    model = Model(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="MODEL-INACTIVE-001",
        name="Model with Inactive Spool",
        description="Test model with inactive spool",
        machine="Ender 3",
        print_time_minutes=180,
        prints_per_plate=1,
        is_active=True,
    )
    db_session.add(model)
    await db_session.flush()

    # Create inactive spool (empty/depleted)
    spool_inactive = Spool(
        id=uuid4(),
        tenant_id=test_tenant.id,
        material_type_id=test_material_type.id,
        spool_id="TEST-INACTIVE-001",
        brand="Generic",
        color="Black",
        color_hex="#000000",
        initial_weight=Decimal("1000.0"),
        current_weight=Decimal("0.0"),  # Empty
        purchase_price=Decimal("20.00"),
        is_active=False,  # Inactive
    )
    db_session.add(spool_inactive)
    await db_session.flush()

    # Add BOM material with inactive spool
    model_material = ModelMaterial(
        id=uuid4(),
        model_id=model.id,
        spool_id=spool_inactive.id,
        weight_grams=Decimal("100.0"),
        cost_per_gram=Decimal("0.020"),
    )
    db_session.add(model_material)

    await db_session.commit()
    await db_session.refresh(model)
    return model


class TestModelsProductionDefaultsEndpoint:
    """Tests for GET /api/v1/models/{model_id}/production-defaults endpoint."""

    @pytest.mark.asyncio
    async def test_get_production_defaults_no_bom(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_model: Model,
    ):
        """Test production defaults endpoint with model that has no BOM."""
        response = await client.get(
            f"/api/v1/models/{test_model.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify model basic info
        assert data["model_id"] == str(test_model.id)
        assert data["sku"] == test_model.sku
        assert data["name"] == test_model.name
        assert data["print_time_minutes"] == test_model.print_time_minutes
        assert data["prints_per_plate"] == 1

        # Verify empty BOM
        assert isinstance(data["bom_materials"], list)
        assert len(data["bom_materials"]) == 0

    @pytest.mark.asyncio
    async def test_get_production_defaults_single_material(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_model_with_single_material_bom: Model,
    ):
        """Test production defaults endpoint with model that has single material in BOM."""
        response = await client.get(
            f"/api/v1/models/{test_model_with_single_material_bom.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify model basic info
        assert data["model_id"] == str(test_model_with_single_material_bom.id)
        assert data["sku"] == "MODEL-SINGLE-001"
        assert data["name"] == "Single Material Model"
        assert data["machine"] == "Prusa i3 MK3S"
        assert data["print_time_minutes"] == 120
        assert data["prints_per_plate"] == 1

        # Verify BOM has one material
        assert len(data["bom_materials"]) == 1

        bom = data["bom_materials"][0]
        assert "spool_id" in bom
        assert bom["spool_name"] == "Test Brand - PLA - Red"
        assert bom["material_type_code"] == "PLA"
        assert bom["color"] == "Red"
        assert float(bom["weight_grams"]) == 50.5
        assert float(bom["cost_per_gram"]) == 0.025
        assert float(bom["current_weight"]) == 800.0
        assert bom["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_production_defaults_multi_material(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_model_with_multi_material_bom: Model,
    ):
        """Test production defaults endpoint with model that has multiple materials in BOM."""
        response = await client.get(
            f"/api/v1/models/{test_model_with_multi_material_bom.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify model info
        assert data["model_id"] == str(test_model_with_multi_material_bom.id)
        assert data["sku"] == "MODEL-MULTI-001"
        assert data["machine"] == "Prusa XL"
        assert data["print_time_minutes"] == 480
        assert data["prints_per_plate"] == 5

        # Verify BOM has two materials
        assert len(data["bom_materials"]) == 2

        # Verify first material (Blue)
        bom_blue = data["bom_materials"][0]
        assert bom_blue["color"] == "Blue"
        assert bom_blue["color_hex"] == "#0000FF"
        assert bom_blue["material_type_code"] == "PLA"
        assert float(bom_blue["weight_grams"]) == 50.0
        assert float(bom_blue["current_weight"]) == 800.0
        assert bom_blue["is_active"] is True

        # Verify second material (Red)
        bom_red = data["bom_materials"][1]
        assert bom_red["color"] == "Red"
        assert bom_red["color_hex"] == "#FF0000"
        assert bom_red["material_type_code"] == "PLA"
        assert float(bom_red["weight_grams"]) == 30.0
        assert float(bom_red["current_weight"]) == 600.0
        assert bom_red["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_production_defaults_inactive_spool(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_model_with_inactive_spool_bom: Model,
    ):
        """Test production defaults endpoint with model that has inactive spool in BOM."""
        response = await client.get(
            f"/api/v1/models/{test_model_with_inactive_spool_bom.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify BOM includes inactive spool (app should warn user, not filter)
        assert len(data["bom_materials"]) == 1

        bom = data["bom_materials"][0]
        assert bom["color"] == "Black"
        assert float(bom["current_weight"]) == 0.0
        assert bom["is_active"] is False  # Frontend can use this to show warning

    @pytest.mark.asyncio
    async def test_get_production_defaults_model_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test production defaults endpoint with non-existent model."""
        non_existent_id = uuid4()
        response = await client.get(
            f"/api/v1/models/{non_existent_id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_production_defaults_batch_printing(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_model_with_multi_material_bom: Model,
    ):
        """Test production defaults endpoint with batch printing model (prints_per_plate > 1)."""
        response = await client.get(
            f"/api/v1/models/{test_model_with_multi_material_bom.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify batch printing settings
        assert data["prints_per_plate"] == 5
        assert data["print_time_minutes"] == 480

        # Calculate time per item: 480 / 5 = 96 minutes
        time_per_item = data["print_time_minutes"] / data["prints_per_plate"]
        assert time_per_item == 96.0

    @pytest.mark.asyncio
    async def test_get_production_defaults_zero_print_time(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test production defaults endpoint with model that has zero print time."""
        # Create model with zero print time
        model = Model(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="MODEL-ZERO-TIME-001",
            name="Zero Print Time Model",
            description="Test model with zero print time",
            machine="Test Printer",
            print_time_minutes=0,  # Zero print time
            prints_per_plate=1,
            is_active=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        response = await client.get(
            f"/api/v1/models/{model.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify endpoint returns zero print time correctly
        assert data["print_time_minutes"] == 0
        assert data["prints_per_plate"] == 1

    @pytest.mark.asyncio
    async def test_get_production_defaults_zero_prints_per_plate(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test production defaults endpoint with model that has zero prints_per_plate.

        This edge case tests database constraint handling - prints_per_plate should
        never be zero (would cause division by zero in calculations), but we test
        that the endpoint doesn't crash if bad data exists.
        """
        # Create model with zero prints_per_plate (edge case/data integrity issue)
        model = Model(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="MODEL-ZERO-PPP-001",
            name="Zero Prints Per Plate Model",
            description="Test model with zero prints per plate",
            machine="Test Printer",
            print_time_minutes=120,
            prints_per_plate=0,  # Zero - would cause division by zero
            is_active=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        response = await client.get(
            f"/api/v1/models/{model.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify endpoint returns the data (frontend should handle division by zero)
        assert data["print_time_minutes"] == 120
        assert data["prints_per_plate"] == 0  # Frontend must validate this

    @pytest.mark.asyncio
    async def test_get_production_defaults_zero_weight_material(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_tenant,
        test_spool: Spool,
    ):
        """Test production defaults endpoint with model that has zero weight BOM material."""
        # Create model with zero weight material
        model = Model(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="MODEL-ZERO-WEIGHT-001",
            name="Zero Weight Material Model",
            description="Test model with zero weight material",
            machine="Test Printer",
            print_time_minutes=120,
            prints_per_plate=1,
            is_active=True,
        )
        db_session.add(model)
        await db_session.flush()

        # Add BOM material with zero weight
        model_material = ModelMaterial(
            id=uuid4(),
            model_id=model.id,
            spool_id=test_spool.id,
            weight_grams=Decimal("0.0"),  # Zero weight
            cost_per_gram=Decimal("0.025"),
        )
        db_session.add(model_material)

        await db_session.commit()
        await db_session.refresh(model)

        response = await client.get(
            f"/api/v1/models/{model.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify BOM includes zero weight material
        assert len(data["bom_materials"]) == 1
        bom = data["bom_materials"][0]
        assert float(bom["weight_grams"]) == 0.0
        assert float(bom["cost_per_gram"]) == 0.025

    @pytest.mark.asyncio
    async def test_get_production_defaults_null_machine(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_tenant,
    ):
        """Test production defaults endpoint with model that has null machine field."""
        # Create model without machine specified (optional field)
        model = Model(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="MODEL-NULL-MACHINE-001",
            name="Model Without Machine",
            description="Test model without machine specified",
            machine=None,  # Null machine
            print_time_minutes=120,
            prints_per_plate=1,
            is_active=True,
        )
        db_session.add(model)
        await db_session.commit()
        await db_session.refresh(model)

        response = await client.get(
            f"/api/v1/models/{model.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify null machine is handled correctly
        assert data["machine"] is None
        assert data["print_time_minutes"] == 120

    @pytest.mark.asyncio
    async def test_get_production_defaults_large_scale_calculations(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_tenant,
        test_spool: Spool,
    ):
        """Test production defaults endpoint with large-scale calculations.

        Tests that the endpoint handles very large print times and weights correctly,
        which would be used for quantity calculations like:
        - 72 hour print (4320 minutes) × 1000 items = 72,000 hours
        - 5000g material × 1000 items = 5,000,000g (5 tons)
        """
        # Create model with very large values
        model = Model(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="MODEL-LARGE-001",
            name="Large Scale Model",
            description="Test model with large print time and material weight",
            machine="Industrial Printer",
            print_time_minutes=4320,  # 72 hours
            prints_per_plate=10,
            is_active=True,
        )
        db_session.add(model)
        await db_session.flush()

        # Add BOM material with large weight
        model_material = ModelMaterial(
            id=uuid4(),
            model_id=model.id,
            spool_id=test_spool.id,
            weight_grams=Decimal("5000.0"),  # 5kg per item
            cost_per_gram=Decimal("0.025"),
        )
        db_session.add(model_material)

        await db_session.commit()
        await db_session.refresh(model)

        response = await client.get(
            f"/api/v1/models/{model.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify large values are returned correctly
        assert data["print_time_minutes"] == 4320
        assert data["prints_per_plate"] == 10
        assert len(data["bom_materials"]) == 1
        assert float(data["bom_materials"][0]["weight_grams"]) == 5000.0

        # Test calculation: time per item = 4320 / 10 = 432 minutes (7.2 hours)
        time_per_item = data["print_time_minutes"] / data["prints_per_plate"]
        assert time_per_item == 432.0

    @pytest.mark.asyncio
    async def test_get_production_defaults_mixed_zero_nonzero_materials(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_tenant,
        test_material_type: MaterialType,
    ):
        """Test production defaults endpoint with mix of zero and non-zero weight materials.

        Tests aggregation when BOM has some materials with zero weight (e.g., support
        material that's not tracked) and some with regular weight.
        """
        # Create model
        model = Model(
            id=uuid4(),
            tenant_id=test_tenant.id,
            sku="MODEL-MIXED-WEIGHT-001",
            name="Mixed Weight Materials Model",
            description="Test model with mixed zero/non-zero material weights",
            machine="Prusa i3",
            print_time_minutes=180,
            prints_per_plate=1,
            is_active=True,
        )
        db_session.add(model)
        await db_session.flush()

        # Create multiple spools
        spool_primary = Spool(
            id=uuid4(),
            tenant_id=test_tenant.id,
            material_type_id=test_material_type.id,
            spool_id="PRIMARY-001",
            brand="eSun",
            color="Black",
            color_hex="#000000",
            initial_weight=Decimal("1000.0"),
            current_weight=Decimal("900.0"),
            purchase_price=Decimal("25.00"),
            is_active=True,
        )
        spool_support = Spool(
            id=uuid4(),
            tenant_id=test_tenant.id,
            material_type_id=test_material_type.id,
            spool_id="SUPPORT-001",
            brand="Generic",
            color="White",
            color_hex="#FFFFFF",
            initial_weight=Decimal("1000.0"),
            current_weight=Decimal("800.0"),
            purchase_price=Decimal("20.00"),
            is_active=True,
        )
        db_session.add_all([spool_primary, spool_support])
        await db_session.flush()

        # Add BOM materials: one with weight, one zero (support material not tracked)
        model_materials = [
            ModelMaterial(
                id=uuid4(),
                model_id=model.id,
                spool_id=spool_primary.id,
                weight_grams=Decimal("100.0"),  # Normal weight
                cost_per_gram=Decimal("0.025"),
            ),
            ModelMaterial(
                id=uuid4(),
                model_id=model.id,
                spool_id=spool_support.id,
                weight_grams=Decimal("0.0"),  # Zero weight (not tracked)
                cost_per_gram=Decimal("0.020"),
            ),
        ]
        db_session.add_all(model_materials)

        await db_session.commit()
        await db_session.refresh(model)

        response = await client.get(
            f"/api/v1/models/{model.id}/production-defaults",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify both materials are returned
        assert len(data["bom_materials"]) == 2

        # Verify first material (primary)
        primary_bom = next(m for m in data["bom_materials"] if m["color"] == "Black")
        assert float(primary_bom["weight_grams"]) == 100.0

        # Verify second material (support - zero weight)
        support_bom = next(m for m in data["bom_materials"] if m["color"] == "White")
        assert float(support_bom["weight_grams"]) == 0.0

        # Total weight aggregation: 100 + 0 = 100g
        total_weight = sum(float(m["weight_grams"]) for m in data["bom_materials"])
        assert total_weight == 100.0
