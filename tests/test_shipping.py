"""Shipping service tests."""

import pytest
from decimal import Decimal

from app.services.shipping import (
    ShippingCarrier,
    ShippingRate,
    ShippingService,
    ShippingZone,
    shipping_service,
)


class TestShippingZone:
    def test_us_mapping(self):
        assert ShippingZone.from_country("US") == ShippingZone.US

    def test_uk_mapping(self):
        assert ShippingZone.from_country("GB") == ShippingZone.UK

    def test_eu_mapping(self):
        assert ShippingZone.from_country("DE") == ShippingZone.EU
        assert ShippingZone.from_country("FR") == ShippingZone.EU
        assert ShippingZone.from_country("IT") == ShippingZone.EU

    def test_jp_mapping(self):
        assert ShippingZone.from_country("JP") == ShippingZone.JP

    def test_sea_mapping(self):
        assert ShippingZone.from_country("SG") == ShippingZone.SEA
        assert ShippingZone.from_country("TH") == ShippingZone.SEA

    def test_unknown_country_defaults_to_us(self):
        assert ShippingZone.from_country("XX") == ShippingZone.US

    def test_case_insensitive(self):
        assert ShippingZone.from_country("us") == ShippingZone.US
        assert ShippingZone.from_country("gb") == ShippingZone.UK


class TestShippingRate:
    def test_basic_calculation(self):
        rate = ShippingRate(
            carrier=ShippingCarrier.FOURPX,
            zone=ShippingZone.US,
            base_rate_usd=Decimal("2.50"),
            per_kg_rate_usd=Decimal("5.00"),
            estimated_days_min=7,
            estimated_days_max=15,
        )
        cost = rate.calculate(Decimal("1.0"))
        assert cost == Decimal("7.50")

    def test_volumetric_weight(self):
        rate = ShippingRate(
            carrier=ShippingCarrier.FOURPX,
            zone=ShippingZone.US,
            base_rate_usd=Decimal("2.00"),
            per_kg_rate_usd=Decimal("5.00"),
            estimated_days_min=7,
            estimated_days_max=15,
            volumetric_divisor=5000,
        )
        # 50x40x30 = 60000 / 5000 = 12kg volumetric > 1kg actual
        cost = rate.calculate(
            Decimal("1.0"),
            length_cm=Decimal("50"),
            width_cm=Decimal("40"),
            height_cm=Decimal("30"),
        )
        assert cost == Decimal("62.00")  # 2 + 12*5

    def test_min_weight_enforced(self):
        rate = ShippingRate(
            carrier=ShippingCarrier.FOURPX,
            zone=ShippingZone.US,
            base_rate_usd=Decimal("2.00"),
            per_kg_rate_usd=Decimal("10.00"),
            estimated_days_min=7,
            estimated_days_max=15,
            min_weight_kg=Decimal("0.5"),
        )
        cost = rate.calculate(Decimal("0.1"))
        assert cost == Decimal("7.00")  # Uses 0.5kg min

    def test_max_weight_exceeded(self):
        rate = ShippingRate(
            carrier=ShippingCarrier.FOURPX,
            zone=ShippingZone.US,
            base_rate_usd=Decimal("2.00"),
            per_kg_rate_usd=Decimal("5.00"),
            estimated_days_min=7,
            estimated_days_max=15,
            max_weight_kg=Decimal("10"),
        )
        with pytest.raises(ValueError, match="exceeds"):
            rate.calculate(Decimal("15.0"))

    def test_surcharges_applied(self):
        rate = ShippingRate(
            carrier=ShippingCarrier.FOURPX,
            zone=ShippingZone.US,
            base_rate_usd=Decimal("2.00"),
            per_kg_rate_usd=Decimal("5.00"),
            estimated_days_min=7,
            estimated_days_max=15,
            surcharges={"fuel": Decimal("1.50"), "remote": Decimal("2.00")},
        )
        cost = rate.calculate(Decimal("1.0"))
        assert cost == Decimal("10.50")  # 2 + 5 + 1.5 + 2


class TestShippingService:
    def test_get_quotes_us(self):
        quotes = shipping_service.get_quotes(Decimal("0.5"), "US")
        assert len(quotes) > 0
        assert all(q.zone == "US" for q in quotes)

    def test_quotes_sorted_by_cost(self):
        quotes = shipping_service.get_quotes(Decimal("1.0"), "US")
        costs = [q.cost_usd for q in quotes]
        assert costs == sorted(costs)

    def test_cheapest_quote(self):
        cheapest = shipping_service.cheapest_quote(Decimal("0.5"), "US")
        assert cheapest is not None
        all_quotes = shipping_service.get_quotes(Decimal("0.5"), "US")
        assert cheapest.cost_usd == all_quotes[0].cost_usd

    def test_fastest_quote(self):
        fastest = shipping_service.fastest_quote(Decimal("0.5"), "US")
        assert fastest is not None

    def test_available_carriers_us(self):
        carriers = shipping_service.available_carriers("US")
        assert len(carriers) >= 3
        assert "4PX" in carriers

    def test_available_carriers_jp(self):
        carriers = shipping_service.available_carriers("JP")
        assert len(carriers) >= 1

    def test_supported_zones(self):
        zones = shipping_service.supported_zones()
        assert "US" in zones
        assert "EU" in zones

    def test_filter_by_carrier(self):
        quotes = shipping_service.get_quotes(
            Decimal("1.0"), "US", carriers=["4PX"]
        )
        assert all(q.carrier == "4PX" for q in quotes)

    def test_no_quotes_for_empty_rate_table(self):
        svc = ShippingService(rate_table={})
        quotes = svc.get_quotes(Decimal("1.0"), "US")
        assert len(quotes) == 0
