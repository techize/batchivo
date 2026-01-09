"""CSV import/export utilities for product data."""

import csv
import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ProductCSVRow(BaseModel):
    """Schema for product CSV row validation."""

    id: Optional[str] = None
    name: str
    sku: str
    category: Optional[str] = None
    description: Optional[str] = None
    designer: Optional[str] = None
    source: Optional[str] = None
    machine: Optional[str] = None
    print_time: Optional[str] = None  # Format: "13h38m" or minutes
    last_printed_date: Optional[str] = None  # Format: DD/MM/YYYY
    units_in_stock: Optional[int] = 0
    labor_hours: Optional[float] = None
    labor_rate: Optional[float] = None
    overhead_percentage: Optional[float] = None
    cost: Optional[float] = None
    sell_price: Optional[float] = None
    # Multi-material support (up to 4 materials)
    filament_1: Optional[str] = None
    weight_1: Optional[float] = None
    filament_2: Optional[str] = None
    weight_2: Optional[float] = None
    filament_3: Optional[str] = None
    weight_3: Optional[float] = None
    filament_4: Optional[str] = None
    weight_4: Optional[float] = None


class CSVImportError(Exception):
    """Raised when CSV import fails validation."""

    pass


def parse_print_time(time_str: Optional[str]) -> Optional[int]:
    """
    Parse print time string to minutes.

    Supports formats:
    - "13h38m" -> 818 minutes
    - "2h" -> 120 minutes
    - "45m" -> 45 minutes
    - "123" -> 123 minutes (raw number)
    - None/empty -> None

    Args:
        time_str: Time string to parse

    Returns:
        Total minutes as integer, or None if input is None/empty
    """
    if not time_str or not time_str.strip():
        return None

    time_str = time_str.strip().lower()

    # If it's just a number, return it directly
    if time_str.isdigit():
        return int(time_str)

    # Parse "XhYm" format
    hours = 0
    minutes = 0

    # Extract hours
    hour_match = re.search(r"(\d+)h", time_str)
    if hour_match:
        hours = int(hour_match.group(1))

    # Extract minutes
    minute_match = re.search(r"(\d+)m", time_str)
    if minute_match:
        minutes = int(minute_match.group(1))

    if hours == 0 and minutes == 0:
        # No valid format found
        raise CSVImportError(
            f"Invalid print time format: '{time_str}'. Expected format: '13h38m', '2h', '45m', or '123'"
        )

    return (hours * 60) + minutes


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse date string to datetime.

    Supports formats:
    - DD/MM/YYYY -> datetime
    - YYYY-MM-DD -> datetime (ISO format)
    - None/empty -> None

    Args:
        date_str: Date string to parse

    Returns:
        datetime object, or None if input is None/empty
    """
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    # Try DD/MM/YYYY format first
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        pass

    # Try ISO format (YYYY-MM-DD)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise CSVImportError(
            f"Invalid date format: '{date_str}'. Expected format: DD/MM/YYYY or YYYY-MM-DD"
        )


def format_print_time(minutes: Optional[int]) -> str:
    """
    Format minutes to "XhYm" string.

    Args:
        minutes: Total minutes

    Returns:
        Formatted string like "13h38m" or empty string if None
    """
    if minutes is None:
        return ""

    hours = minutes // 60
    mins = minutes % 60

    if hours > 0 and mins > 0:
        return f"{hours}h{mins}m"
    elif hours > 0:
        return f"{hours}h"
    elif mins > 0:
        return f"{mins}m"
    else:
        return "0m"


def format_date(dt: Optional[datetime]) -> str:
    """
    Format datetime to DD/MM/YYYY string.

    Args:
        dt: datetime object

    Returns:
        Formatted date string or empty string if None
    """
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y")


def parse_csv_file(csv_content: str) -> List[ProductCSVRow]:
    """
    Parse CSV content into validated product rows.

    Args:
        csv_content: CSV file content as string

    Returns:
        List of validated ProductCSVRow objects

    Raises:
        CSVImportError: If CSV validation fails
    """
    rows = []
    reader = csv.DictReader(io.StringIO(csv_content))

    if not reader.fieldnames:
        raise CSVImportError("CSV file is empty or has no headers")

    # Normalize fieldnames (lowercase, strip spaces)
    {name.strip().lower(): name for name in reader.fieldnames}

    for idx, raw_row in enumerate(reader, start=2):  # Start at 2 (1 = header)
        try:
            # Normalize row keys
            row = {
                key.strip().lower(): value.strip() if value else None
                for key, value in raw_row.items()
            }

            # Required fields
            if not row.get("name"):
                raise CSVImportError(f"Row {idx}: 'name' is required")
            if not row.get("sku"):
                raise CSVImportError(f"Row {idx}: 'sku' is required")

            # Create validated row
            validated_row = ProductCSVRow(
                id=row.get("id"),
                name=row["name"],
                sku=row["sku"],
                category=row.get("category"),
                description=row.get("description"),
                designer=row.get("designer"),
                source=row.get("source"),
                machine=row.get("machine"),
                print_time=row.get("print time") or row.get("print_time"),
                last_printed_date=row.get("date printed last") or row.get("last_printed_date"),
                units_in_stock=int(row["units"]) if row.get("units") else 0,
                labor_hours=float(row["labor_hours"]) if row.get("labor_hours") else None,
                labor_rate=float(row["labor_rate"]) if row.get("labor_rate") else None,
                overhead_percentage=float(row["overhead_percentage"])
                if row.get("overhead_percentage")
                else None,
                cost=float(row["cost"]) if row.get("cost") else None,
                sell_price=float(row["sell"]) if row.get("sell") else None,
                # Multi-material mapping
                filament_1=row.get("filament1") or row.get("filament_1"),
                weight_1=float(row["weight1"])
                if row.get("weight1") or row.get("weight_1")
                else None,
                filament_2=row.get("filament2") or row.get("filament_2"),
                weight_2=float(row["weight2"])
                if row.get("weight2") or row.get("weight_2")
                else None,
                filament_3=row.get("filament3") or row.get("filament_3"),
                weight_3=float(row["weight3"])
                if row.get("weight3") or row.get("weight_3")
                else None,
                filament_4=row.get("filament4") or row.get("filament_4"),
                weight_4=float(row["weight4"])
                if row.get("weight4") or row.get("weight_4")
                else None,
            )

            rows.append(validated_row)

        except (ValueError, KeyError) as e:
            raise CSVImportError(f"Row {idx}: {str(e)}")

    if not rows:
        raise CSVImportError("No valid rows found in CSV file")

    return rows


def generate_csv_export(products: List[Dict[str, Any]]) -> str:
    """
    Generate CSV export from product data.

    Args:
        products: List of product dictionaries

    Returns:
        CSV content as string
    """
    output = io.StringIO()
    fieldnames = [
        "ID",
        "Name",
        "SKU",
        "Category",
        "Description",
        "Designer",
        "Source",
        "Machine",
        "Print Time",
        "Date Printed Last",
        "Units",
        "Labor Hours",
        "Labor Rate",
        "Overhead %",
        "Cost",
        "Sell",
        "Filament1",
        "Weight1",
        "Filament2",
        "Weight2",
        "Filament3",
        "Weight3",
        "Filament4",
        "Weight4",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for product in products:
        # Extract material info (up to 4 materials)
        materials = product.get("materials", [])[:4]
        material_data = {}

        for i, material in enumerate(materials, start=1):
            spool = material.get("spool", {})
            material_data[f"Filament{i}"] = (
                f"{spool.get('material_type', '')} - {spool.get('color', '')}"
            )
            material_data[f"Weight{i}"] = material.get("weight_grams", "")

        # Build row
        row = {
            "ID": str(product.get("id", "")),
            "Name": product.get("name", ""),
            "SKU": product.get("sku", ""),
            "Category": product.get("category", ""),
            "Description": product.get("description", ""),
            "Designer": product.get("designer", ""),
            "Source": product.get("source", ""),
            "Machine": product.get("machine", ""),
            "Print Time": format_print_time(product.get("print_time_minutes")),
            "Date Printed Last": format_date(product.get("last_printed_date")),
            "Units": product.get("units_in_stock", 0),
            "Labor Hours": product.get("labor_hours", ""),
            "Labor Rate": product.get("labor_rate", ""),
            "Overhead %": product.get("overhead_percentage", ""),
            "Cost": product.get("cost_breakdown", {}).get("total_cost", ""),
            "Sell": "",  # Not stored currently
            **material_data,
        }

        writer.writerow(row)

    return output.getvalue()
