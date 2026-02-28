"""Shipping rate calculator for cross-border logistics.

Supports multiple carriers common in China→World cross-border e-commerce.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class ShippingCarrier(str, Enum):
    """Supported shipping carriers."""
    FOURPX = "4PX"
    YUNEXPRESS = "YunExpress"
    YANWEN = "Yanwen"
    CAINIAO = "Cainiao"
    DHL_ECOMMERCE = "DHL_eCommerce"
    UBI = "UBI"
    CHINA_POST = "ChinaPost"
    EMS = "EMS"
    FEDEX = "FedEx"
    UPS = "UPS"
    SF_EXPRESS = "SF_Express"
    JCEX = "JCEX"


class ShippingZone(str, Enum):
    """Destination zones."""
    US = "US"
    EU = "EU"
    UK = "UK"
    CA = "CA"
    AU = "AU"
    JP = "JP"
    SEA = "SEA"  # Southeast Asia
    SA = "SA"    # South America
    ME = "ME"    # Middle East
    AF = "AF"    # Africa
    RU = "RU"    # Russia/CIS

    @classmethod
    def from_country(cls, country_code: str) -> "ShippingZone":
        """Map ISO 3166-1 alpha-2 to zone."""
        mapping = {
            "US": cls.US, "CA": cls.CA, "MX": cls.US,
            "GB": cls.UK, "DE": cls.EU, "FR": cls.EU, "IT": cls.EU,
            "ES": cls.EU, "NL": cls.EU, "BE": cls.EU, "PL": cls.EU,
            "SE": cls.EU, "AT": cls.EU, "PT": cls.EU, "IE": cls.EU,
            "AU": cls.AU, "NZ": cls.AU,
            "JP": cls.JP, "KR": cls.JP,
            "SG": cls.SEA, "MY": cls.SEA, "TH": cls.SEA, "ID": cls.SEA,
            "PH": cls.SEA, "VN": cls.SEA,
            "BR": cls.SA, "AR": cls.SA, "CL": cls.SA, "CO": cls.SA,
            "AE": cls.ME, "SA": cls.ME, "IL": cls.ME, "TR": cls.ME,
            "RU": cls.RU, "UA": cls.RU, "KZ": cls.RU,
            "ZA": cls.AF, "NG": cls.AF, "KE": cls.AF, "EG": cls.AF,
        }
        return mapping.get(country_code.upper(), cls.US)


@dataclass
class ShippingRate:
    """Single shipping rate quote."""
    carrier: ShippingCarrier
    zone: ShippingZone
    base_rate_usd: Decimal
    per_kg_rate_usd: Decimal
    estimated_days_min: int
    estimated_days_max: int
    tracking: bool = True
    insurance_available: bool = False
    max_weight_kg: Decimal = Decimal("30")
    min_weight_kg: Decimal = Decimal("0.01")
    volumetric_divisor: int = 5000  # L*W*H / divisor
    surcharges: dict[str, Decimal] = field(default_factory=dict)

    def calculate(
        self,
        weight_kg: Decimal,
        length_cm: Decimal = Decimal("0"),
        width_cm: Decimal = Decimal("0"),
        height_cm: Decimal = Decimal("0"),
    ) -> Decimal:
        """Calculate shipping cost for a package."""
        # Use volumetric weight if larger
        actual_weight = weight_kg
        if length_cm > 0 and width_cm > 0 and height_cm > 0:
            vol_weight = (length_cm * width_cm * height_cm) / self.volumetric_divisor
            actual_weight = max(weight_kg, vol_weight)

        # Enforce limits
        if actual_weight < self.min_weight_kg:
            actual_weight = self.min_weight_kg
        if actual_weight > self.max_weight_kg:
            raise ValueError(
                f"Weight {actual_weight}kg exceeds {self.carrier.value} max {self.max_weight_kg}kg"
            )

        cost = self.base_rate_usd + (actual_weight * self.per_kg_rate_usd)

        # Apply surcharges
        for name, amount in self.surcharges.items():
            cost += amount

        return cost.quantize(Decimal("0.01"))


@dataclass
class ShippingQuote:
    """Complete shipping quote with multiple options."""
    carrier: str
    service: str
    cost_usd: Decimal
    estimated_days: str
    tracking: bool
    weight_kg: Decimal
    zone: str


# ── Rate Tables ─────────────────────────────────────────

_RATE_TABLE: dict[str, dict[str, ShippingRate]] = {
    ShippingCarrier.FOURPX: {
        ShippingZone.US: ShippingRate(
            carrier=ShippingCarrier.FOURPX, zone=ShippingZone.US,
            base_rate_usd=Decimal("2.50"), per_kg_rate_usd=Decimal("5.80"),
            estimated_days_min=7, estimated_days_max=15,
        ),
        ShippingZone.EU: ShippingRate(
            carrier=ShippingCarrier.FOURPX, zone=ShippingZone.EU,
            base_rate_usd=Decimal("3.00"), per_kg_rate_usd=Decimal("6.50"),
            estimated_days_min=8, estimated_days_max=18,
        ),
        ShippingZone.UK: ShippingRate(
            carrier=ShippingCarrier.FOURPX, zone=ShippingZone.UK,
            base_rate_usd=Decimal("2.80"), per_kg_rate_usd=Decimal("6.00"),
            estimated_days_min=7, estimated_days_max=15,
        ),
        ShippingZone.AU: ShippingRate(
            carrier=ShippingCarrier.FOURPX, zone=ShippingZone.AU,
            base_rate_usd=Decimal("3.20"), per_kg_rate_usd=Decimal("7.00"),
            estimated_days_min=8, estimated_days_max=18,
        ),
        ShippingZone.JP: ShippingRate(
            carrier=ShippingCarrier.FOURPX, zone=ShippingZone.JP,
            base_rate_usd=Decimal("2.00"), per_kg_rate_usd=Decimal("4.50"),
            estimated_days_min=5, estimated_days_max=10,
        ),
        ShippingZone.SEA: ShippingRate(
            carrier=ShippingCarrier.FOURPX, zone=ShippingZone.SEA,
            base_rate_usd=Decimal("1.80"), per_kg_rate_usd=Decimal("3.80"),
            estimated_days_min=5, estimated_days_max=12,
        ),
    },
    ShippingCarrier.YUNEXPRESS: {
        ShippingZone.US: ShippingRate(
            carrier=ShippingCarrier.YUNEXPRESS, zone=ShippingZone.US,
            base_rate_usd=Decimal("2.00"), per_kg_rate_usd=Decimal("5.20"),
            estimated_days_min=8, estimated_days_max=18,
        ),
        ShippingZone.EU: ShippingRate(
            carrier=ShippingCarrier.YUNEXPRESS, zone=ShippingZone.EU,
            base_rate_usd=Decimal("2.50"), per_kg_rate_usd=Decimal("6.00"),
            estimated_days_min=10, estimated_days_max=20,
        ),
        ShippingZone.UK: ShippingRate(
            carrier=ShippingCarrier.YUNEXPRESS, zone=ShippingZone.UK,
            base_rate_usd=Decimal("2.30"), per_kg_rate_usd=Decimal("5.50"),
            estimated_days_min=8, estimated_days_max=16,
        ),
        ShippingZone.SEA: ShippingRate(
            carrier=ShippingCarrier.YUNEXPRESS, zone=ShippingZone.SEA,
            base_rate_usd=Decimal("1.50"), per_kg_rate_usd=Decimal("3.20"),
            estimated_days_min=5, estimated_days_max=10,
        ),
    },
    ShippingCarrier.YANWEN: {
        ShippingZone.US: ShippingRate(
            carrier=ShippingCarrier.YANWEN, zone=ShippingZone.US,
            base_rate_usd=Decimal("1.80"), per_kg_rate_usd=Decimal("4.80"),
            estimated_days_min=10, estimated_days_max=25,
        ),
        ShippingZone.EU: ShippingRate(
            carrier=ShippingCarrier.YANWEN, zone=ShippingZone.EU,
            base_rate_usd=Decimal("2.20"), per_kg_rate_usd=Decimal("5.50"),
            estimated_days_min=12, estimated_days_max=28,
        ),
    },
    ShippingCarrier.CHINA_POST: {
        ShippingZone.US: ShippingRate(
            carrier=ShippingCarrier.CHINA_POST, zone=ShippingZone.US,
            base_rate_usd=Decimal("1.50"), per_kg_rate_usd=Decimal("4.00"),
            estimated_days_min=15, estimated_days_max=45, tracking=False,
        ),
        ShippingZone.EU: ShippingRate(
            carrier=ShippingCarrier.CHINA_POST, zone=ShippingZone.EU,
            base_rate_usd=Decimal("1.80"), per_kg_rate_usd=Decimal("4.50"),
            estimated_days_min=15, estimated_days_max=45, tracking=False,
        ),
    },
    ShippingCarrier.EMS: {
        ShippingZone.US: ShippingRate(
            carrier=ShippingCarrier.EMS, zone=ShippingZone.US,
            base_rate_usd=Decimal("8.00"), per_kg_rate_usd=Decimal("10.00"),
            estimated_days_min=5, estimated_days_max=10, insurance_available=True,
        ),
        ShippingZone.EU: ShippingRate(
            carrier=ShippingCarrier.EMS, zone=ShippingZone.EU,
            base_rate_usd=Decimal("9.00"), per_kg_rate_usd=Decimal("11.00"),
            estimated_days_min=5, estimated_days_max=12, insurance_available=True,
        ),
        ShippingZone.JP: ShippingRate(
            carrier=ShippingCarrier.EMS, zone=ShippingZone.JP,
            base_rate_usd=Decimal("6.00"), per_kg_rate_usd=Decimal("8.00"),
            estimated_days_min=3, estimated_days_max=7, insurance_available=True,
        ),
    },
}


class ShippingService:
    """Cross-border shipping rate calculator."""

    def __init__(self, rate_table: Optional[dict] = None):
        self._rates = _RATE_TABLE if rate_table is None else rate_table

    def get_quotes(
        self,
        weight_kg: Decimal,
        destination_country: str,
        length_cm: Decimal = Decimal("0"),
        width_cm: Decimal = Decimal("0"),
        height_cm: Decimal = Decimal("0"),
        carriers: Optional[list[str]] = None,
    ) -> list[ShippingQuote]:
        """Get shipping quotes from all available carriers for a destination."""
        zone = ShippingZone.from_country(destination_country)
        quotes: list[ShippingQuote] = []

        for carrier_enum, zones in self._rates.items():
            if carriers and carrier_enum.value not in carriers:
                continue
            rate = zones.get(zone)
            if not rate:
                continue
            try:
                cost = rate.calculate(weight_kg, length_cm, width_cm, height_cm)
                quotes.append(ShippingQuote(
                    carrier=carrier_enum.value,
                    service="Standard",
                    cost_usd=cost,
                    estimated_days=f"{rate.estimated_days_min}-{rate.estimated_days_max}",
                    tracking=rate.tracking,
                    weight_kg=weight_kg,
                    zone=zone.value,
                ))
            except ValueError:
                continue

        # Sort by cost
        quotes.sort(key=lambda q: q.cost_usd)
        return quotes

    def cheapest_quote(
        self,
        weight_kg: Decimal,
        destination_country: str,
        **kwargs,
    ) -> Optional[ShippingQuote]:
        """Get the cheapest shipping option."""
        quotes = self.get_quotes(weight_kg, destination_country, **kwargs)
        return quotes[0] if quotes else None

    def fastest_quote(
        self,
        weight_kg: Decimal,
        destination_country: str,
        **kwargs,
    ) -> Optional[ShippingQuote]:
        """Get the fastest shipping option."""
        quotes = self.get_quotes(weight_kg, destination_country, **kwargs)
        if not quotes:
            return None
        # Parse estimated_days and sort by min days
        return min(quotes, key=lambda q: int(q.estimated_days.split("-")[0]))

    def available_carriers(self, destination_country: str) -> list[str]:
        """List carriers that serve a destination country."""
        zone = ShippingZone.from_country(destination_country)
        return [
            carrier.value
            for carrier, zones in self._rates.items()
            if zone in zones
        ]

    def supported_zones(self) -> list[str]:
        """List all supported shipping zones."""
        zones = set()
        for carrier_zones in self._rates.values():
            zones.update(z.value for z in carrier_zones)
        return sorted(zones)


# Module-level singleton
shipping_service = ShippingService()
