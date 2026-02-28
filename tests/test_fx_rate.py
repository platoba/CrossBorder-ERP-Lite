"""FX rate service tests."""

import pytest
from decimal import Decimal

from app.services.fx_rate import FXService


class TestFXService:
    def test_init_default(self):
        fx = FXService()
        assert fx.base_currency == "USD"

    def test_init_custom_base(self):
        fx = FXService(base_currency="eur")
        assert fx.base_currency == "EUR"

    def test_supported_currencies(self):
        fx = FXService()
        currencies = fx.supported_currencies()
        assert "USD" in currencies
        assert "CNY" in currencies
        assert "EUR" in currencies
        assert len(currencies) >= 10

    @pytest.mark.asyncio
    async def test_convert_same_currency(self):
        fx = FXService()
        result = await fx.convert(Decimal("100"), "USD", "USD")
        assert result == Decimal("100")

    @pytest.mark.asyncio
    async def test_convert_usd_to_cny(self):
        fx = FXService()
        result = await fx.convert(Decimal("100"), "USD", "CNY")
        assert result > Decimal("600")  # Should be around 725

    @pytest.mark.asyncio
    async def test_convert_cny_to_usd(self):
        fx = FXService()
        result = await fx.convert(Decimal("725"), "CNY", "USD")
        assert result > Decimal("90")
        assert result < Decimal("110")

    @pytest.mark.asyncio
    async def test_get_rate(self):
        fx = FXService()
        rate = await fx.get_rate("USD", "CNY")
        assert rate > Decimal("5")
        assert rate < Decimal("10")

    @pytest.mark.asyncio
    async def test_convert_case_insensitive(self):
        fx = FXService()
        r1 = await fx.convert(Decimal("100"), "usd", "cny")
        r2 = await fx.convert(Decimal("100"), "USD", "CNY")
        assert r1 == r2

    @pytest.mark.asyncio
    async def test_fetch_rates_uses_cache(self):
        fx = FXService()
        r1 = await fx.fetch_rates()
        r2 = await fx.fetch_rates()
        assert r1 is r2  # Same dict object from cache
