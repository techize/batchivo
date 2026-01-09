"""Tests for shipping rates API endpoints."""

import pytest
from httpx import AsyncClient


class TestShippingEndpoints:
    """Tests for shipping API endpoints."""

    @pytest.mark.asyncio
    async def test_get_shipping_rates_valid_postcode(
        self,
        client: AsyncClient,
    ):
        """Test getting shipping rates for a valid UK postcode."""
        response = await client.post(
            "/api/v1/shipping/rates",
            json={"postcode": "SW1A 1AA"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["postcode_valid"] is True
        assert len(data["options"]) >= 3
        assert data["free_shipping_threshold_pence"] == 5000

        # Check first option structure
        first_option = data["options"][0]
        assert "id" in first_option
        assert "name" in first_option
        assert "carrier" in first_option
        assert "price_pence" in first_option
        assert "is_tracked" in first_option

    @pytest.mark.asyncio
    async def test_get_shipping_rates_invalid_postcode(
        self,
        client: AsyncClient,
    ):
        """Test shipping rates for an invalid postcode."""
        response = await client.post(
            "/api/v1/shipping/rates",
            json={"postcode": "INVALID"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["postcode_valid"] is False
        assert len(data["options"]) == 0

    @pytest.mark.asyncio
    async def test_get_shipping_rates_highland_island(
        self,
        client: AsyncClient,
    ):
        """Test shipping rates for Highland/Island postcode (surcharge applies)."""
        response = await client.post(
            "/api/v1/shipping/rates",
            json={"postcode": "IV1 1AA"},  # Inverness - Highland
        )

        assert response.status_code == 200
        data = response.json()
        assert data["postcode_valid"] is True

        # Check that surcharge is applied (base price + £3)
        # Royal Mail 2nd Class base is 295, with 300 surcharge = 595
        first_option = next((opt for opt in data["options"] if opt["id"] == "royal-mail-2nd"), None)
        assert first_option is not None
        assert first_option["price_pence"] == 595  # 295 + 300 surcharge

    @pytest.mark.asyncio
    async def test_get_shipping_rates_free_shipping(
        self,
        client: AsyncClient,
    ):
        """Test free shipping when cart meets threshold."""
        response = await client.post(
            "/api/v1/shipping/rates",
            json={
                "postcode": "SW1A 1AA",
                "cart_total_pence": 5500,  # £55, above £50 threshold
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["qualifies_for_free_shipping"] is True

        # Check that basic shipping is free
        free_option = next((opt for opt in data["options"] if opt["id"] == "royal-mail-2nd"), None)
        assert free_option is not None
        assert free_option["price_pence"] == 0
        assert "FREE" in free_option["name"]

    @pytest.mark.asyncio
    async def test_validate_postcode_valid(
        self,
        client: AsyncClient,
    ):
        """Test postcode validation for a valid UK postcode."""
        response = await client.get("/api/v1/shipping/validate-postcode/SW1A1AA")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["postcode"] == "SW1A 1AA"  # Normalized
        assert data["area"] == "SW"
        assert data["region"] == "London"
        assert data["is_highland_island"] is False

    @pytest.mark.asyncio
    async def test_validate_postcode_invalid(
        self,
        client: AsyncClient,
    ):
        """Test postcode validation for an invalid postcode."""
        response = await client.get("/api/v1/shipping/validate-postcode/NOTVALID")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    @pytest.mark.asyncio
    async def test_validate_postcode_highland(
        self,
        client: AsyncClient,
    ):
        """Test postcode validation identifies Highland/Island areas."""
        response = await client.get("/api/v1/shipping/validate-postcode/HS12AB")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["is_highland_island"] is True
        assert data["region"] == "Outer Hebrides"

    @pytest.mark.asyncio
    async def test_validate_postcode_northern_ireland(
        self,
        client: AsyncClient,
    ):
        """Test postcode validation for Northern Ireland."""
        response = await client.get("/api/v1/shipping/validate-postcode/BT11AA")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["is_highland_island"] is True
        assert data["region"] == "Northern Ireland"

    @pytest.mark.asyncio
    async def test_list_shipping_methods(
        self,
        client: AsyncClient,
    ):
        """Test listing all available shipping methods."""
        response = await client.get("/api/v1/shipping/methods")

        assert response.status_code == 200
        data = response.json()
        assert "methods" in data
        assert len(data["methods"]) >= 3
        assert data["free_shipping_threshold_pence"] == 5000
        assert data["highland_island_surcharge_pence"] == 300

        # Check method structure
        first_method = data["methods"][0]
        assert "id" in first_method
        assert "name" in first_method
        assert "carrier" in first_method
        assert "base_price_pence" in first_method
        assert "estimated_days" in first_method
        assert "is_tracked" in first_method

    @pytest.mark.asyncio
    async def test_validate_postcode_normalizes_format(
        self,
        client: AsyncClient,
    ):
        """Test that postcode is normalized to standard format."""
        # Test lowercase and no space
        response = await client.get("/api/v1/shipping/validate-postcode/sw1a1aa")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["postcode"] == "SW1A 1AA"  # Normalized to uppercase with space

    @pytest.mark.asyncio
    async def test_validate_postcode_channel_islands(
        self,
        client: AsyncClient,
    ):
        """Test postcode validation for Channel Islands."""
        # Jersey
        response = await client.get("/api/v1/shipping/validate-postcode/JE12AB")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["is_highland_island"] is True
        assert data["region"] == "Channel Islands"

        # Guernsey
        response = await client.get("/api/v1/shipping/validate-postcode/GY12AB")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["is_highland_island"] is True
