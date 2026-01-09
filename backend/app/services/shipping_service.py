"""Shipping rates service.

Provides shipping rate calculations with UK postcode validation.
Currently uses hardcoded rates, structured for Royal Mail API integration later.
"""

import re
from typing import Optional

from app.schemas.shipping import (
    PostcodeValidationResponse,
    ShippingOption,
    ShippingRatesResponse,
)


# UK postcode regex pattern
# Matches formats: AA9A 9AA, A9A 9AA, A9 9AA, A99 9AA, AA9 9AA, AA99 9AA
UK_POSTCODE_REGEX = re.compile(
    r"^([A-Z]{1,2}[0-9][A-Z0-9]?\s?[0-9][A-Z]{2})$",
    re.IGNORECASE,
)

# Scottish Highlands and Islands postcodes (surcharge areas)
HIGHLAND_ISLAND_PREFIXES = {
    "AB",  # Aberdeen (some parts)
    "BT",  # Northern Ireland
    "FK",  # Falkirk (some parts)
    "GY",  # Guernsey
    "HS",  # Outer Hebrides
    "IM",  # Isle of Man
    "IV",  # Inverness
    "JE",  # Jersey
    "KA",  # Kilmarnock (Arran)
    "KW",  # Kirkwall (Orkney)
    "PA",  # Paisley (some islands)
    "PH",  # Perth (Highlands)
    "ZE",  # Shetland
}

# More specific Highland/Island postcodes
HIGHLAND_ISLAND_FULL_PREFIXES = {
    "AB31",
    "AB32",
    "AB33",
    "AB34",
    "AB35",
    "AB36",
    "AB37",
    "AB38",
    "AB41",
    "AB42",
    "AB43",
    "AB44",
    "AB45",
    "AB51",
    "AB52",
    "AB53",
    "AB54",
    "AB55",
    "AB56",
    "FK17",
    "FK18",
    "FK19",
    "FK20",
    "FK21",
    "KA27",
    "KA28",
    "PA20",
    "PA21",
    "PA22",
    "PA23",
    "PA24",
    "PA25",
    "PA26",
    "PA27",
    "PA28",
    "PA29",
    "PA30",
    "PA31",
    "PA32",
    "PA33",
    "PA34",
    "PA35",
    "PA36",
    "PA37",
    "PA38",
    "PA39",
    "PA40",
    "PA41",
    "PA42",
    "PA43",
    "PA44",
    "PA45",
    "PA46",
    "PA47",
    "PA48",
    "PA49",
    "PA60",
    "PA61",
    "PA62",
    "PA63",
    "PA64",
    "PA65",
    "PA66",
    "PA67",
    "PA68",
    "PA69",
    "PA70",
    "PA71",
    "PA72",
    "PA73",
    "PA74",
    "PA75",
    "PA76",
    "PA77",
    "PA78",
    "PH15",
    "PH16",
    "PH17",
    "PH18",
    "PH19",
    "PH20",
    "PH21",
    "PH22",
    "PH23",
    "PH24",
    "PH25",
    "PH26",
    "PH30",
    "PH31",
    "PH32",
    "PH33",
    "PH34",
    "PH35",
    "PH36",
    "PH37",
    "PH38",
    "PH39",
    "PH40",
    "PH41",
    "PH42",
    "PH43",
    "PH44",
    "PH49",
    "PH50",
}


class ShippingService:
    """Service for calculating shipping rates.

    Currently uses hardcoded UK rates. Structured for Royal Mail API integration.
    """

    # Configuration
    FREE_SHIPPING_THRESHOLD_PENCE = 5000  # £50 for free shipping
    HIGHLAND_ISLAND_SURCHARGE_PENCE = 300  # £3 surcharge

    # Standard shipping options (mainland UK)
    STANDARD_OPTIONS = [
        ShippingOption(
            id="royal-mail-2nd",
            name="Royal Mail 2nd Class",
            carrier="Royal Mail",
            description="2-3 working days",
            price_pence=295,  # £2.95
            estimated_days_min=2,
            estimated_days_max=3,
            is_tracked=False,
            is_signed=False,
        ),
        ShippingOption(
            id="royal-mail-tracked-48",
            name="Royal Mail Tracked 48",
            carrier="Royal Mail",
            description="2 working days (tracked)",
            price_pence=395,  # £3.95
            estimated_days_min=1,
            estimated_days_max=2,
            is_tracked=True,
            is_signed=False,
        ),
        ShippingOption(
            id="royal-mail-tracked-24",
            name="Royal Mail Tracked 24",
            carrier="Royal Mail",
            description="Next working day (tracked)",
            price_pence=595,  # £5.95
            estimated_days_min=1,
            estimated_days_max=1,
            is_tracked=True,
            is_signed=False,
        ),
        ShippingOption(
            id="royal-mail-special-delivery",
            name="Royal Mail Special Delivery",
            carrier="Royal Mail",
            description="Next day by 1pm (tracked & signed)",
            price_pence=895,  # £8.95
            estimated_days_min=1,
            estimated_days_max=1,
            is_tracked=True,
            is_signed=True,
        ),
    ]

    def normalize_postcode(self, postcode: str) -> str:
        """Normalize a UK postcode to standard format (uppercase, with space)."""
        # Remove all whitespace and convert to uppercase
        cleaned = postcode.strip().upper().replace(" ", "")

        # Insert space before the inward code (last 3 characters)
        if len(cleaned) >= 5:
            return f"{cleaned[:-3]} {cleaned[-3:]}"
        return cleaned

    def validate_postcode(self, postcode: str) -> PostcodeValidationResponse:
        """Validate a UK postcode and return area information."""
        normalized = self.normalize_postcode(postcode)

        # Check against regex
        if not UK_POSTCODE_REGEX.match(normalized):
            return PostcodeValidationResponse(
                valid=False,
                postcode=normalized,
                area=None,
                region=None,
                is_highland_island=False,
            )

        # Extract area code (first 1-2 letters)
        area_match = re.match(r"^([A-Z]{1,2})", normalized)
        area = area_match.group(1) if area_match else None

        # Extract district (letters + numbers before space)
        district_match = re.match(r"^([A-Z]{1,2}[0-9]{1,2}[A-Z]?)", normalized)
        district = district_match.group(1) if district_match else None

        # Check if Highland/Island
        is_highland_island = False
        if district and district in HIGHLAND_ISLAND_FULL_PREFIXES:
            is_highland_island = True
        elif area in {"HS", "IM", "JE", "GY", "ZE", "KW"}:
            is_highland_island = True
        elif area == "IV" and district:
            # Most IV postcodes are Highland
            is_highland_island = True
        elif area == "BT":
            # Northern Ireland
            is_highland_island = True

        # Determine region
        region = self._get_region_for_area(area, is_highland_island)

        return PostcodeValidationResponse(
            valid=True,
            postcode=normalized,
            area=area,
            region=region,
            is_highland_island=is_highland_island,
        )

    def _get_region_for_area(self, area: Optional[str], is_highland_island: bool) -> Optional[str]:
        """Get region name for a postcode area."""
        if not area:
            return None

        # Simple mapping of major areas
        regions = {
            "AB": "Scotland",
            "B": "West Midlands",
            "BA": "Somerset",
            "BB": "Lancashire",
            "BD": "West Yorkshire",
            "BH": "Dorset",
            "BL": "Greater Manchester",
            "BN": "East Sussex",
            "BR": "Greater London",
            "BS": "Bristol",
            "BT": "Northern Ireland",
            "CA": "Cumbria",
            "CB": "Cambridgeshire",
            "CF": "South Wales",
            "CH": "Cheshire",
            "CM": "Essex",
            "CO": "Essex",
            "CR": "Greater London",
            "CT": "Kent",
            "CV": "West Midlands",
            "CW": "Cheshire",
            "DA": "Kent",
            "DD": "Scotland",
            "DE": "Derbyshire",
            "DG": "Scotland",
            "DH": "County Durham",
            "DL": "County Durham",
            "DN": "South Yorkshire",
            "DT": "Dorset",
            "DY": "West Midlands",
            "E": "London",
            "EC": "London",
            "EH": "Scotland",
            "EN": "Hertfordshire",
            "EX": "Devon",
            "FK": "Scotland",
            "FY": "Lancashire",
            "G": "Scotland",
            "GL": "Gloucestershire",
            "GU": "Surrey",
            "GY": "Channel Islands",
            "HA": "Greater London",
            "HD": "West Yorkshire",
            "HG": "North Yorkshire",
            "HP": "Buckinghamshire",
            "HR": "Herefordshire",
            "HS": "Outer Hebrides",
            "HU": "East Yorkshire",
            "HX": "West Yorkshire",
            "IG": "Greater London",
            "IM": "Isle of Man",
            "IP": "Suffolk",
            "IV": "Scottish Highlands",
            "JE": "Channel Islands",
            "KA": "Scotland",
            "KT": "Surrey",
            "KW": "Orkney",
            "KY": "Scotland",
            "L": "Merseyside",
            "LA": "Lancashire",
            "LD": "Wales",
            "LE": "Leicestershire",
            "LL": "North Wales",
            "LN": "Lincolnshire",
            "LS": "West Yorkshire",
            "LU": "Bedfordshire",
            "M": "Greater Manchester",
            "ME": "Kent",
            "MK": "Buckinghamshire",
            "ML": "Scotland",
            "N": "London",
            "NE": "Tyne and Wear",
            "NG": "Nottinghamshire",
            "NN": "Northamptonshire",
            "NP": "South Wales",
            "NR": "Norfolk",
            "NW": "London",
            "OL": "Greater Manchester",
            "OX": "Oxfordshire",
            "PA": "Scotland",
            "PE": "Cambridgeshire",
            "PH": "Scottish Highlands",
            "PL": "Devon",
            "PO": "Hampshire",
            "PR": "Lancashire",
            "RG": "Berkshire",
            "RH": "Surrey",
            "RM": "Essex",
            "S": "South Yorkshire",
            "SA": "South Wales",
            "SE": "London",
            "SG": "Hertfordshire",
            "SK": "Cheshire",
            "SL": "Berkshire",
            "SM": "Greater London",
            "SN": "Wiltshire",
            "SO": "Hampshire",
            "SP": "Wiltshire",
            "SR": "Tyne and Wear",
            "SS": "Essex",
            "ST": "Staffordshire",
            "SW": "London",
            "SY": "Shropshire",
            "TA": "Somerset",
            "TD": "Scotland",
            "TF": "Shropshire",
            "TN": "Kent",
            "TQ": "Devon",
            "TR": "Cornwall",
            "TS": "North Yorkshire",
            "TW": "Greater London",
            "UB": "Greater London",
            "W": "London",
            "WA": "Cheshire",
            "WC": "London",
            "WD": "Hertfordshire",
            "WF": "West Yorkshire",
            "WN": "Greater Manchester",
            "WR": "Worcestershire",
            "WS": "West Midlands",
            "WV": "West Midlands",
            "YO": "North Yorkshire",
            "ZE": "Shetland",
        }

        region = regions.get(area)
        if region:
            return region

        # Default based on Highland/Island status
        if is_highland_island:
            return "Scottish Highlands & Islands"
        return "United Kingdom"

    async def get_shipping_rates(
        self,
        postcode: str,
        weight_grams: Optional[int] = None,
        cart_total_pence: Optional[int] = None,
    ) -> ShippingRatesResponse:
        """Get available shipping rates for a postcode.

        Args:
            postcode: UK delivery postcode
            weight_grams: Total package weight (for future weight-based pricing)
            cart_total_pence: Cart total for free shipping calculation

        Returns:
            ShippingRatesResponse with available options
        """
        # Validate postcode
        validation = self.validate_postcode(postcode)

        if not validation.valid:
            return ShippingRatesResponse(
                options=[],
                postcode_valid=False,
                free_shipping_threshold_pence=self.FREE_SHIPPING_THRESHOLD_PENCE,
                qualifies_for_free_shipping=False,
            )

        # Check free shipping eligibility
        qualifies_for_free = (
            cart_total_pence is not None and cart_total_pence >= self.FREE_SHIPPING_THRESHOLD_PENCE
        )

        # Build options list
        options = []
        for base_option in self.STANDARD_OPTIONS:
            price = base_option.price_pence

            # Apply Highland/Island surcharge
            if validation.is_highland_island:
                price += self.HIGHLAND_ISLAND_SURCHARGE_PENCE
                # Also add 1 day to delivery estimate for remote areas
                option = ShippingOption(
                    id=base_option.id,
                    name=base_option.name,
                    carrier=base_option.carrier,
                    description=f"{base_option.description} (+£3 remote area)",
                    price_pence=price,
                    estimated_days_min=base_option.estimated_days_min + 1,
                    estimated_days_max=base_option.estimated_days_max + 1,
                    is_tracked=base_option.is_tracked,
                    is_signed=base_option.is_signed,
                )
            else:
                option = ShippingOption(
                    id=base_option.id,
                    name=base_option.name,
                    carrier=base_option.carrier,
                    description=base_option.description,
                    price_pence=price,
                    estimated_days_min=base_option.estimated_days_min,
                    estimated_days_max=base_option.estimated_days_max,
                    is_tracked=base_option.is_tracked,
                    is_signed=base_option.is_signed,
                )

            # Apply free shipping if eligible (on cheapest option only)
            if qualifies_for_free and option.id == "royal-mail-2nd":
                option = ShippingOption(
                    id=option.id,
                    name=f"{option.name} (FREE)",
                    carrier=option.carrier,
                    description=option.description,
                    price_pence=0,
                    estimated_days_min=option.estimated_days_min,
                    estimated_days_max=option.estimated_days_max,
                    is_tracked=option.is_tracked,
                    is_signed=option.is_signed,
                )

            options.append(option)

        return ShippingRatesResponse(
            options=options,
            postcode_valid=True,
            free_shipping_threshold_pence=self.FREE_SHIPPING_THRESHOLD_PENCE,
            qualifies_for_free_shipping=qualifies_for_free,
        )

    def get_shipping_cost(
        self,
        shipping_method_id: str,
        postcode: str,
        cart_total_pence: Optional[int] = None,
    ) -> tuple[str, int]:
        """Get the cost for a specific shipping method.

        Args:
            shipping_method_id: The shipping method ID
            postcode: Delivery postcode
            cart_total_pence: Cart total for free shipping calculation

        Returns:
            Tuple of (method_name, price_pence)
        """
        validation = self.validate_postcode(postcode)

        # Find the base option
        base_option = None
        for opt in self.STANDARD_OPTIONS:
            if opt.id == shipping_method_id:
                base_option = opt
                break

        if not base_option:
            # Default fallback
            return ("Standard Shipping", 395)

        price = base_option.price_pence

        # Apply Highland/Island surcharge
        if validation.valid and validation.is_highland_island:
            price += self.HIGHLAND_ISLAND_SURCHARGE_PENCE

        # Apply free shipping if eligible
        qualifies_for_free = (
            cart_total_pence is not None
            and cart_total_pence >= self.FREE_SHIPPING_THRESHOLD_PENCE
            and shipping_method_id == "royal-mail-2nd"
        )

        if qualifies_for_free:
            price = 0

        return (base_option.name, price)


# Singleton instance for dependency injection
_shipping_service: Optional[ShippingService] = None


def get_shipping_service() -> ShippingService:
    """Get the shipping service instance."""
    global _shipping_service
    if _shipping_service is None:
        _shipping_service = ShippingService()
    return _shipping_service
