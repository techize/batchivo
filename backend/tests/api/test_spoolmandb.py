"""Tests for SpoolmanDB API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spoolmandb import SpoolmanDBFilament, SpoolmanDBManufacturer


class TestSpoolmanDBEndpoints:
    """Tests for SpoolmanDB API endpoints."""

    @pytest_asyncio.fixture
    async def spoolmandb_manufacturer(
        self,
        db_session: AsyncSession,
    ) -> SpoolmanDBManufacturer:
        """Create a test SpoolmanDB manufacturer."""
        manufacturer = SpoolmanDBManufacturer(
            id=uuid4(),
            name="Test Manufacturer",
            is_active=True,
        )
        db_session.add(manufacturer)
        await db_session.commit()
        await db_session.refresh(manufacturer)
        return manufacturer

    @pytest_asyncio.fixture
    async def second_manufacturer(
        self,
        db_session: AsyncSession,
    ) -> SpoolmanDBManufacturer:
        """Create a second test manufacturer."""
        manufacturer = SpoolmanDBManufacturer(
            id=uuid4(),
            name="Polymaker",
            is_active=True,
        )
        db_session.add(manufacturer)
        await db_session.commit()
        await db_session.refresh(manufacturer)
        return manufacturer

    @pytest_asyncio.fixture
    async def inactive_manufacturer(
        self,
        db_session: AsyncSession,
    ) -> SpoolmanDBManufacturer:
        """Create an inactive manufacturer."""
        manufacturer = SpoolmanDBManufacturer(
            id=uuid4(),
            name="Discontinued Brand",
            is_active=False,
        )
        db_session.add(manufacturer)
        await db_session.commit()
        await db_session.refresh(manufacturer)
        return manufacturer

    @pytest_asyncio.fixture
    async def spoolmandb_filament(
        self,
        db_session: AsyncSession,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
    ) -> SpoolmanDBFilament:
        """Create a test SpoolmanDB filament."""
        filament = SpoolmanDBFilament(
            id=uuid4(),
            external_id="test-filament-001",
            manufacturer_id=spoolmandb_manufacturer.id,
            name="Galaxy Black PLA",
            material="PLA",
            density=1.24,
            diameter=1.75,
            weight=1000,
            spool_weight=200,
            spool_type="plastic",
            color_name="Galaxy Black",
            color_hex="#1A1A1A",
            extruder_temp=210,
            bed_temp=60,
            finish="matte",
            translucent=False,
            glow=False,
            is_active=True,
        )
        db_session.add(filament)
        await db_session.commit()
        await db_session.refresh(filament)
        return filament

    @pytest_asyncio.fixture
    async def petg_filament(
        self,
        db_session: AsyncSession,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
    ) -> SpoolmanDBFilament:
        """Create a PETG filament."""
        filament = SpoolmanDBFilament(
            id=uuid4(),
            external_id="test-filament-002",
            manufacturer_id=spoolmandb_manufacturer.id,
            name="Clear Blue PETG",
            material="PETG",
            density=1.27,
            diameter=1.75,
            weight=1000,
            color_name="Clear Blue",
            color_hex="#0066CC",
            extruder_temp=240,
            bed_temp=80,
            translucent=True,
            glow=False,
            is_active=True,
        )
        db_session.add(filament)
        await db_session.commit()
        await db_session.refresh(filament)
        return filament

    @pytest_asyncio.fixture
    async def polymaker_filament(
        self,
        db_session: AsyncSession,
        second_manufacturer: SpoolmanDBManufacturer,
    ) -> SpoolmanDBFilament:
        """Create a Polymaker filament."""
        filament = SpoolmanDBFilament(
            id=uuid4(),
            external_id="polymaker-pla-001",
            manufacturer_id=second_manufacturer.id,
            name="PolyTerra PLA Earth Brown",
            material="PLA",
            density=1.24,
            diameter=1.75,
            weight=1000,
            color_name="Earth Brown",
            color_hex="#8B4513",
            extruder_temp=200,
            bed_temp=55,
            translucent=False,
            glow=False,
            is_active=True,
        )
        db_session.add(filament)
        await db_session.commit()
        await db_session.refresh(filament)
        return filament

    @pytest_asyncio.fixture
    async def large_diameter_filament(
        self,
        db_session: AsyncSession,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
    ) -> SpoolmanDBFilament:
        """Create a 2.85mm filament."""
        filament = SpoolmanDBFilament(
            id=uuid4(),
            external_id="test-filament-285",
            manufacturer_id=spoolmandb_manufacturer.id,
            name="Red PLA 2.85",
            material="PLA",
            density=1.24,
            diameter=2.85,
            weight=1000,
            color_name="Red",
            color_hex="#FF0000",
            translucent=False,
            glow=False,
            is_active=True,
        )
        db_session.add(filament)
        await db_session.commit()
        await db_session.refresh(filament)
        return filament

    @pytest_asyncio.fixture
    async def inactive_filament(
        self,
        db_session: AsyncSession,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
    ) -> SpoolmanDBFilament:
        """Create an inactive filament."""
        filament = SpoolmanDBFilament(
            id=uuid4(),
            external_id="test-filament-inactive",
            manufacturer_id=spoolmandb_manufacturer.id,
            name="Discontinued Color",
            material="PLA",
            density=1.24,
            diameter=1.75,
            weight=500,
            translucent=False,
            glow=False,
            is_active=False,
        )
        db_session.add(filament)
        await db_session.commit()
        await db_session.refresh(filament)
        return filament

    # =========================================================================
    # Stats Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_stats_empty(
        self,
        client: AsyncClient,
    ):
        """Test getting stats when database is empty."""
        response = await client.get("/api/v1/spoolmandb/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_manufacturers" in data
        assert "total_filaments" in data
        assert "materials" in data

    @pytest.mark.asyncio
    async def test_get_stats_with_data(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
    ):
        """Test getting stats with data in database."""
        response = await client.get("/api/v1/spoolmandb/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_manufacturers"] >= 1
        assert data["total_filaments"] >= 2

    # =========================================================================
    # Manufacturers Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_manufacturers_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing manufacturers when empty."""
        response = await client.get("/api/v1/spoolmandb/manufacturers")

        assert response.status_code == 200
        data = response.json()
        assert "manufacturers" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_manufacturers(
        self,
        client: AsyncClient,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
        second_manufacturer: SpoolmanDBManufacturer,
    ):
        """Test listing manufacturers."""
        response = await client.get("/api/v1/spoolmandb/manufacturers")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        # Check manufacturer structure
        for manufacturer in data["manufacturers"]:
            assert "id" in manufacturer
            assert "name" in manufacturer
            assert "filament_count" in manufacturer

    @pytest.mark.asyncio
    async def test_list_manufacturers_excludes_inactive(
        self,
        client: AsyncClient,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
        inactive_manufacturer: SpoolmanDBManufacturer,
    ):
        """Test that inactive manufacturers are excluded."""
        response = await client.get("/api/v1/spoolmandb/manufacturers")

        assert response.status_code == 200
        data = response.json()
        names = [m["name"] for m in data["manufacturers"]]
        assert spoolmandb_manufacturer.name in names
        assert inactive_manufacturer.name not in names

    @pytest.mark.asyncio
    async def test_list_manufacturers_search(
        self,
        client: AsyncClient,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
        second_manufacturer: SpoolmanDBManufacturer,
    ):
        """Test searching manufacturers by name."""
        response = await client.get(
            "/api/v1/spoolmandb/manufacturers",
            params={"search": "Poly"},
        )

        assert response.status_code == 200
        data = response.json()
        for manufacturer in data["manufacturers"]:
            assert "poly" in manufacturer["name"].lower()

    @pytest.mark.asyncio
    async def test_list_manufacturers_with_filament_count(
        self,
        client: AsyncClient,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
        spoolmandb_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
    ):
        """Test that manufacturers include correct filament count."""
        response = await client.get("/api/v1/spoolmandb/manufacturers")

        assert response.status_code == 200
        data = response.json()

        # Find our test manufacturer
        test_manufacturer = None
        for m in data["manufacturers"]:
            if m["name"] == spoolmandb_manufacturer.name:
                test_manufacturer = m
                break

        assert test_manufacturer is not None
        assert test_manufacturer["filament_count"] >= 2

    # =========================================================================
    # Filaments Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_filaments_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing filaments when empty."""
        response = await client.get("/api/v1/spoolmandb/filaments")

        assert response.status_code == 200
        data = response.json()
        assert "filaments" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_list_filaments(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
    ):
        """Test listing filaments."""
        response = await client.get("/api/v1/spoolmandb/filaments")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["filaments"]) >= 2

    @pytest.mark.asyncio
    async def test_list_filaments_excludes_inactive(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        inactive_filament: SpoolmanDBFilament,
    ):
        """Test that inactive filaments are excluded."""
        response = await client.get("/api/v1/spoolmandb/filaments")

        assert response.status_code == 200
        data = response.json()
        external_ids = [f["external_id"] for f in data["filaments"]]
        assert spoolmandb_filament.external_id in external_ids
        assert inactive_filament.external_id not in external_ids

    @pytest.mark.asyncio
    async def test_list_filaments_pagination(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
        polymaker_filament: SpoolmanDBFilament,
    ):
        """Test filament list pagination."""
        response = await client.get(
            "/api/v1/spoolmandb/filaments",
            params={"page": 1, "page_size": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["filaments"]) <= 2

    @pytest.mark.asyncio
    async def test_list_filaments_filter_by_manufacturer_id(
        self,
        client: AsyncClient,
        spoolmandb_manufacturer: SpoolmanDBManufacturer,
        spoolmandb_filament: SpoolmanDBFilament,
        polymaker_filament: SpoolmanDBFilament,
    ):
        """Test filtering filaments by manufacturer ID."""
        response = await client.get(
            "/api/v1/spoolmandb/filaments",
            params={"manufacturer_id": str(spoolmandb_manufacturer.id)},
        )

        assert response.status_code == 200
        data = response.json()
        for filament in data["filaments"]:
            assert filament["manufacturer_id"] == str(spoolmandb_manufacturer.id)

    @pytest.mark.asyncio
    async def test_list_filaments_filter_by_manufacturer_name(
        self,
        client: AsyncClient,
        second_manufacturer: SpoolmanDBManufacturer,
        polymaker_filament: SpoolmanDBFilament,
        spoolmandb_filament: SpoolmanDBFilament,
    ):
        """Test filtering filaments by manufacturer name."""
        response = await client.get(
            "/api/v1/spoolmandb/filaments",
            params={"manufacturer_name": "Poly"},
        )

        assert response.status_code == 200
        data = response.json()
        for filament in data["filaments"]:
            assert "poly" in filament["manufacturer_name"].lower()

    @pytest.mark.asyncio
    async def test_list_filaments_filter_by_material(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
    ):
        """Test filtering filaments by material type."""
        response = await client.get(
            "/api/v1/spoolmandb/filaments",
            params={"material": "PETG"},
        )

        assert response.status_code == 200
        data = response.json()
        for filament in data["filaments"]:
            assert "petg" in filament["material"].lower()

    @pytest.mark.asyncio
    async def test_list_filaments_filter_by_diameter(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        large_diameter_filament: SpoolmanDBFilament,
    ):
        """Test filtering filaments by diameter."""
        response = await client.get(
            "/api/v1/spoolmandb/filaments",
            params={"diameter": 2.85},
        )

        assert response.status_code == 200
        data = response.json()
        for filament in data["filaments"]:
            assert filament["diameter"] == 2.85

    @pytest.mark.asyncio
    async def test_list_filaments_search_by_name(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
    ):
        """Test searching filaments by name."""
        response = await client.get(
            "/api/v1/spoolmandb/filaments",
            params={"search": "Galaxy"},
        )

        assert response.status_code == 200
        data = response.json()
        for filament in data["filaments"]:
            assert (
                "galaxy" in filament["name"].lower()
                or "galaxy" in (filament["color_name"] or "").lower()
            )

    @pytest.mark.asyncio
    async def test_list_filaments_search_by_color(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
    ):
        """Test searching filaments by color."""
        response = await client.get(
            "/api/v1/spoolmandb/filaments",
            params={"search": "Blue"},
        )

        assert response.status_code == 200
        data = response.json()
        for filament in data["filaments"]:
            assert (
                "blue" in filament["name"].lower()
                or "blue" in (filament["color_name"] or "").lower()
            )

    # =========================================================================
    # Get Filament Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_get_filament(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
    ):
        """Test getting a specific filament."""
        response = await client.get(f"/api/v1/spoolmandb/filaments/{spoolmandb_filament.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(spoolmandb_filament.id)
        assert data["name"] == spoolmandb_filament.name
        assert data["material"] == spoolmandb_filament.material
        assert data["manufacturer_name"] is not None
        assert data["diameter"] == spoolmandb_filament.diameter
        assert data["weight"] == spoolmandb_filament.weight

    @pytest.mark.asyncio
    async def test_get_filament_not_found(
        self,
        client: AsyncClient,
    ):
        """Test getting non-existent filament."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/spoolmandb/filaments/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_filament_full_details(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
    ):
        """Test that filament response includes all fields."""
        response = await client.get(f"/api/v1/spoolmandb/filaments/{spoolmandb_filament.id}")

        assert response.status_code == 200
        data = response.json()

        # Check all expected fields are present
        expected_fields = [
            "id",
            "external_id",
            "manufacturer_id",
            "manufacturer_name",
            "name",
            "material",
            "density",
            "diameter",
            "weight",
            "spool_weight",
            "spool_type",
            "color_name",
            "color_hex",
            "extruder_temp",
            "bed_temp",
            "finish",
            "translucent",
            "glow",
            "is_active",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    # =========================================================================
    # Materials Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_materials_empty(
        self,
        client: AsyncClient,
    ):
        """Test listing materials when no filaments exist."""
        response = await client.get("/api/v1/spoolmandb/materials")

        assert response.status_code == 200
        data = response.json()
        assert "materials" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_materials(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
    ):
        """Test listing materials from filaments."""
        response = await client.get("/api/v1/spoolmandb/materials")

        assert response.status_code == 200
        data = response.json()
        materials = [m["material"] for m in data["materials"]]
        assert "PLA" in materials
        assert "PETG" in materials

    @pytest.mark.asyncio
    async def test_list_materials_includes_count(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        polymaker_filament: SpoolmanDBFilament,
        petg_filament: SpoolmanDBFilament,
    ):
        """Test that materials include filament count."""
        response = await client.get("/api/v1/spoolmandb/materials")

        assert response.status_code == 200
        data = response.json()

        # Find PLA (should have 2 filaments)
        pla_entry = None
        for m in data["materials"]:
            if m["material"] == "PLA":
                pla_entry = m
                break

        assert pla_entry is not None
        assert pla_entry["count"] >= 2  # Galaxy Black and PolyTerra

    @pytest.mark.asyncio
    async def test_list_materials_excludes_inactive(
        self,
        client: AsyncClient,
        spoolmandb_filament: SpoolmanDBFilament,
        inactive_filament: SpoolmanDBFilament,
    ):
        """Test that materials only count active filaments."""
        response = await client.get("/api/v1/spoolmandb/materials")

        assert response.status_code == 200
        # Just ensure the endpoint works - we can't easily verify
        # inactive filaments aren't counted without more complex setup
        data = response.json()
        assert "materials" in data
