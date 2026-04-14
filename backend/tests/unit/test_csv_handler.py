"""Unit tests for CSV handler utilities."""

from datetime import datetime

import pytest

from app.utils.csv_handler import (
    CSVImportError,
    format_date,
    format_print_time,
    generate_csv_export,
    parse_csv_file,
    parse_date,
    parse_print_time,
)


class TestParsePrintTime:
    """Tests for parse_print_time."""

    def test_none_returns_none(self):
        assert parse_print_time(None) is None

    def test_empty_string_returns_none(self):
        assert parse_print_time("") is None

    def test_whitespace_returns_none(self):
        assert parse_print_time("   ") is None

    def test_raw_number_minutes(self):
        assert parse_print_time("123") == 123

    def test_hours_and_minutes(self):
        assert parse_print_time("13h38m") == (13 * 60) + 38

    def test_hours_only(self):
        assert parse_print_time("2h") == 120

    def test_minutes_only(self):
        assert parse_print_time("45m") == 45

    def test_zero_minutes_raises(self):
        # "0m" resolves to hours=0, minutes=0 — treated as invalid
        with pytest.raises(CSVImportError):
            parse_print_time("0m")

    def test_large_value(self):
        assert parse_print_time("24h0m") == 1440

    def test_case_insensitive(self):
        assert parse_print_time("2H30M") == 150

    def test_strips_whitespace(self):
        assert parse_print_time("  2h  ") == 120

    def test_invalid_format_raises(self):
        with pytest.raises(CSVImportError, match="Invalid print time format"):
            parse_print_time("invalid")


class TestParseDate:
    """Tests for parse_date."""

    def test_none_returns_none(self):
        assert parse_date(None) is None

    def test_empty_string_returns_none(self):
        assert parse_date("") is None

    def test_whitespace_returns_none(self):
        assert parse_date("   ") is None

    def test_dd_mm_yyyy_format(self):
        result = parse_date("25/12/2025")
        assert isinstance(result, datetime)
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2025

    def test_iso_format(self):
        result = parse_date("2025-12-25")
        assert isinstance(result, datetime)
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2025

    def test_strips_whitespace(self):
        result = parse_date("  25/12/2025  ")
        assert result is not None
        assert result.day == 25

    def test_invalid_format_raises(self):
        with pytest.raises(CSVImportError, match="Invalid date format"):
            parse_date("12-25-2025")


class TestFormatPrintTime:
    """Tests for format_print_time."""

    def test_none_returns_empty_string(self):
        assert format_print_time(None) == ""

    def test_zero_returns_zero_minutes(self):
        assert format_print_time(0) == "0m"

    def test_minutes_only(self):
        assert format_print_time(45) == "45m"

    def test_hours_only(self):
        assert format_print_time(120) == "2h"

    def test_hours_and_minutes(self):
        assert format_print_time(818) == "13h38m"

    def test_exact_hour_boundary(self):
        assert format_print_time(60) == "1h"

    def test_roundtrip_with_parse_nonzero(self):
        # Only non-zero values round-trip cleanly
        original = 818  # 13h38m
        formatted = format_print_time(original)
        parsed = parse_print_time(formatted)
        assert parsed == original


class TestFormatDate:
    """Tests for format_date."""

    def test_none_returns_empty_string(self):
        assert format_date(None) == ""

    def test_formats_to_dd_mm_yyyy(self):
        dt = datetime(2025, 12, 25)
        assert format_date(dt) == "25/12/2025"

    def test_pads_single_digit_day_and_month(self):
        dt = datetime(2025, 1, 5)
        assert format_date(dt) == "05/01/2025"

    def test_roundtrip_with_parse(self):
        dt = datetime(2025, 6, 15)
        formatted = format_date(dt)
        parsed = parse_date(formatted)
        assert parsed == dt


class TestParseCsvFile:
    """Tests for parse_csv_file."""

    MINIMAL_CSV = "name,sku\nTest Dragon,PROD-001\n"
    FULL_CSV = (
        "name,sku,category,description,units,cost,sell\n"
        "Test Dragon,PROD-001,dragons,A dragon,3,10.50,45.00\n"
    )

    def test_parses_minimal_row(self):
        rows = parse_csv_file(self.MINIMAL_CSV)
        assert len(rows) == 1
        assert rows[0].name == "Test Dragon"
        assert rows[0].sku == "PROD-001"

    def test_parses_optional_fields(self):
        rows = parse_csv_file(self.FULL_CSV)
        assert rows[0].category == "dragons"
        assert rows[0].description == "A dragon"
        assert rows[0].units_in_stock == 3
        assert rows[0].cost == pytest.approx(10.50)
        assert rows[0].sell_price == pytest.approx(45.00)

    def test_parses_multiple_rows(self):
        csv = "name,sku\nDragon A,PROD-001\nDragon B,PROD-002\n"
        rows = parse_csv_file(csv)
        assert len(rows) == 2
        assert rows[0].name == "Dragon A"
        assert rows[1].name == "Dragon B"

    def test_missing_name_raises(self):
        csv = "name,sku\n,PROD-001\n"
        with pytest.raises(CSVImportError, match="'name' is required"):
            parse_csv_file(csv)

    def test_missing_sku_raises(self):
        csv = "name,sku\nTest Dragon,\n"
        with pytest.raises(CSVImportError, match="'sku' is required"):
            parse_csv_file(csv)

    def test_empty_csv_raises(self):
        with pytest.raises(CSVImportError):
            parse_csv_file("")

    def test_headers_only_no_rows_raises(self):
        with pytest.raises(CSVImportError, match="No valid rows found"):
            parse_csv_file("name,sku\n")

    def test_normalises_column_names(self):
        # Column names with mixed case and spaces
        csv = "Name , SKU\nTest Dragon,PROD-001\n"
        rows = parse_csv_file(csv)
        assert rows[0].name == "Test Dragon"


class TestGenerateCsvExport:
    """Tests for generate_csv_export."""

    def test_returns_string(self):
        result = generate_csv_export([])
        assert isinstance(result, str)

    def test_empty_products_returns_header_only(self):
        result = generate_csv_export([])
        lines = result.strip().splitlines()
        assert len(lines) == 1  # header only
        assert "Name" in lines[0]
        assert "SKU" in lines[0]

    def test_includes_product_name_and_sku(self):
        products = [{"id": "p1", "name": "Test Dragon", "sku": "PROD-001"}]
        result = generate_csv_export(products)
        assert "Test Dragon" in result
        assert "PROD-001" in result

    def test_includes_material_data(self):
        products = [{
            "id": "p1",
            "name": "Test",
            "sku": "PROD-001",
            "materials": [
                {"spool": {"material_type": "PLA", "color": "Red"}, "weight_grams": 50}
            ],
        }]
        result = generate_csv_export(products)
        assert "PLA" in result
        assert "Red" in result
        assert "50" in result

    def test_handles_multiple_products(self):
        products = [
            {"id": "p1", "name": "Dragon A", "sku": "PROD-001"},
            {"id": "p2", "name": "Dragon B", "sku": "PROD-002"},
        ]
        result = generate_csv_export(products)
        lines = result.strip().splitlines()
        assert len(lines) == 3  # header + 2 rows

    def test_roundtrip_name_and_sku(self):
        products = [{"name": "Test Dragon", "sku": "PROD-042"}]
        csv_output = generate_csv_export(products)
        parsed = parse_csv_file(csv_output)
        assert parsed[0].name == "Test Dragon"
        assert parsed[0].sku == "PROD-042"
