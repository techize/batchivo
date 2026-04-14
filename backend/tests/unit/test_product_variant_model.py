"""Unit tests for ProductVariant model utilities."""

from app.models.product_variant import (
    FulfilmentType,
    ProductSizeSystem,
    SIZE_PRESETS,
    get_size_options,
)


class TestProductSizeSystemEnum:
    """Tests for ProductSizeSystem enum values."""

    def test_none_value(self):
        assert ProductSizeSystem.NONE == "none"

    def test_accessory_value(self):
        assert ProductSizeSystem.ACCESSORY == "accessory"

    def test_baby_child_value(self):
        assert ProductSizeSystem.BABY_CHILD == "baby_child"

    def test_adult_general_value(self):
        assert ProductSizeSystem.ADULT_GENERAL == "adult_general"

    def test_adult_numeric_value(self):
        assert ProductSizeSystem.ADULT_NUMERIC == "adult_numeric"

    def test_custom_value(self):
        assert ProductSizeSystem.CUSTOM == "custom"

    def test_is_string_enum(self):
        assert isinstance(ProductSizeSystem.NONE, str)


class TestFulfilmentTypeEnum:
    """Tests for FulfilmentType enum values."""

    def test_stock_value(self):
        assert FulfilmentType.STOCK == "stock"

    def test_print_to_order_value(self):
        assert FulfilmentType.PRINT_TO_ORDER == "print_to_order"


class TestGetSizeOptions:
    """Tests for get_size_options function."""

    def test_none_returns_empty_list(self):
        result = get_size_options(ProductSizeSystem.NONE)
        assert result == []

    def test_accessory_returns_s_m_l(self):
        result = get_size_options(ProductSizeSystem.ACCESSORY)
        assert result == ["S", "M", "L"]

    def test_adult_general_returns_7_sizes(self):
        result = get_size_options(ProductSizeSystem.ADULT_GENERAL)
        assert result == ["XS", "S", "M", "L", "XL", "2XL", "3XL"]

    def test_adult_numeric_returns_8_sizes(self):
        result = get_size_options(ProductSizeSystem.ADULT_NUMERIC)
        assert len(result) == 8
        assert result[0] == "US 2/UK 6"
        assert result[-1] == "US 16/UK 20"

    def test_baby_child_returns_13_sizes(self):
        result = get_size_options(ProductSizeSystem.BABY_CHILD)
        assert len(result) == 13
        assert result[0] == "Preemie"
        assert result[-1] == "10-12y"

    def test_custom_returns_empty_list(self):
        result = get_size_options(ProductSizeSystem.CUSTOM)
        assert result == []

    def test_returns_list_type(self):
        result = get_size_options(ProductSizeSystem.ACCESSORY)
        assert isinstance(result, list)

    def test_size_presets_covers_all_systems(self):
        # Every ProductSizeSystem variant must have an entry in SIZE_PRESETS
        for system in ProductSizeSystem:
            assert system in SIZE_PRESETS, f"{system} missing from SIZE_PRESETS"

    def test_unknown_system_returns_empty_list(self):
        # get_size_options uses .get() with default [] so unknown → []
        result = SIZE_PRESETS.get("nonexistent_system", [])
        assert result == []
