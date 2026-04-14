"""Unit tests for SKUGeneratorService."""

import pytest

from app.services.sku_generator import EntityType, SKUGeneratorService


class TestParseSku:
    """Tests for the pure parse_sku static method."""

    def test_parse_valid_prod_sku(self):
        result = SKUGeneratorService.parse_sku("PROD-001")
        assert result == ("PROD", 1)

    def test_parse_valid_mod_sku(self):
        result = SKUGeneratorService.parse_sku("MOD-042")
        assert result == ("MOD", 42)

    def test_parse_valid_large_number(self):
        result = SKUGeneratorService.parse_sku("FIL-9999")
        assert result == ("FIL", 9999)

    def test_parse_invalid_no_dash(self):
        assert SKUGeneratorService.parse_sku("PROD001") is None

    def test_parse_invalid_lowercase(self):
        assert SKUGeneratorService.parse_sku("prod-001") is None

    def test_parse_invalid_empty(self):
        assert SKUGeneratorService.parse_sku("") is None

    def test_parse_invalid_only_prefix(self):
        assert SKUGeneratorService.parse_sku("PROD-") is None

    def test_parse_invalid_non_numeric_suffix(self):
        assert SKUGeneratorService.parse_sku("PROD-ABC") is None

    def test_parse_returns_integer_number(self):
        result = SKUGeneratorService.parse_sku("COM-007")
        assert result is not None
        assert isinstance(result[1], int)
        assert result[1] == 7


class TestFormatSku:
    """Tests for the pure format_sku static method."""

    def test_format_basic(self):
        assert SKUGeneratorService.format_sku("PROD", 1) == "PROD-001"

    def test_format_pads_to_three_digits(self):
        assert SKUGeneratorService.format_sku("MOD", 42) == "MOD-042"

    def test_format_no_padding_needed(self):
        assert SKUGeneratorService.format_sku("FIL", 999) == "FIL-999"

    def test_format_exceeds_padding(self):
        # Numbers wider than padding should not be truncated
        assert SKUGeneratorService.format_sku("PROD", 1000) == "PROD-1000"

    def test_format_custom_padding(self):
        assert SKUGeneratorService.format_sku("COM", 5, padding=5) == "COM-00005"

    def test_format_roundtrip_with_parse(self):
        sku = SKUGeneratorService.format_sku("PROD", 7)
        parsed = SKUGeneratorService.parse_sku(sku)
        assert parsed == ("PROD", 7)


class TestEntityType:
    """Tests for the EntityType enum."""

    def test_entity_type_values(self):
        assert EntityType.PROD == "PROD"
        assert EntityType.MOD == "MOD"
        assert EntityType.COM == "COM"
        assert EntityType.FIL == "FIL"
        assert EntityType.RUN == "RUN"

    def test_run_not_in_entity_config(self):
        # RUN has no table-backed SKU config — get_highest_sku_number returns 0
        assert EntityType.RUN not in SKUGeneratorService.ENTITY_CONFIG


class TestGetHighestSkuNumber:
    """Tests for get_highest_sku_number against a real DB session."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_skus(self, db_session, test_tenant):
        result = await SKUGeneratorService.get_highest_sku_number(
            db_session, test_tenant.id, EntityType.PROD
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_for_unknown_entity_type(self, db_session, test_tenant):
        # RUN is not in ENTITY_CONFIG
        result = await SKUGeneratorService.get_highest_sku_number(
            db_session, test_tenant.id, EntityType.RUN
        )
        assert result == 0

    @pytest.mark.asyncio
    async def test_accepts_string_tenant_id(self, db_session, test_tenant):
        # Should not raise even when tenant_id passed as string
        result = await SKUGeneratorService.get_highest_sku_number(
            db_session, str(test_tenant.id), EntityType.MOD
        )
        assert result == 0


class TestGenerateNextSku:
    """Tests for generate_next_sku."""

    @pytest.mark.asyncio
    async def test_first_sku_is_001(self, db_session, test_tenant):
        sku = await SKUGeneratorService.generate_next_sku(
            db_session, test_tenant.id, EntityType.PROD
        )
        assert sku == "PROD-001"

    @pytest.mark.asyncio
    async def test_first_mod_sku(self, db_session, test_tenant):
        sku = await SKUGeneratorService.generate_next_sku(
            db_session, test_tenant.id, EntityType.MOD
        )
        assert sku == "MOD-001"

    @pytest.mark.asyncio
    async def test_first_fil_sku(self, db_session, test_tenant):
        sku = await SKUGeneratorService.generate_next_sku(
            db_session, test_tenant.id, EntityType.FIL
        )
        assert sku == "FIL-001"

    @pytest.mark.asyncio
    async def test_result_is_parseable(self, db_session, test_tenant):
        sku = await SKUGeneratorService.generate_next_sku(
            db_session, test_tenant.id, EntityType.COM
        )
        parsed = SKUGeneratorService.parse_sku(sku)
        assert parsed is not None
        assert parsed[0] == "COM"
        assert parsed[1] >= 1
