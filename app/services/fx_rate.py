"""Currency exchange rate service.

Fetches real-time FX rates and caches them for cross-border pricing.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx

# Default fallback rates (updated periodically)
_FALLBACK_RATES: dict[str, float] = {
    "USD": 1.0,
    "CNY": 7.25,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.5,
    "CAD": 1.36,
    "AUD": 1.54,
    "HKD": 7.82,
    "MXN": 17.15,
    "BRL": 4.97,
}

_cache: dict[str, dict] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


class FXService:
    """Currency exchange service with caching."""

    def __init__(self, base_currency: str = "USD"):
        self.base_currency = base_currency.upper()
        self._rates: dict[str, float] = dict(_FALLBACK_RATES)
        self._last_fetch: Optional[datetime] = None

    async def fetch_rates(self, force: bool = False) -> dict[str, float]:
        """Fetch latest rates from free API, fallback to cached/defaults."""
        now = datetime.now(timezone.utc)
        if not force and self._last_fetch:
            elapsed = (now - self._last_fetch).total_seconds()
            if elapsed < _CACHE_TTL_SECONDS:
                return self._rates

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://api.exchangerate-api.com/v4/latest/{self.base_currency}"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._rates = data.get("rates", self._rates)
                    self._last_fetch = now
        except (httpx.HTTPError, Exception):
            pass  # Use fallback/cached rates

        return self._rates

    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
    ) -> Decimal:
        """Convert amount between currencies."""
        from_c = from_currency.upper()
        to_c = to_currency.upper()
        if from_c == to_c:
            return amount

        rates = await self.fetch_rates()
        from_rate = Decimal(str(rates.get(from_c, 1.0)))
        to_rate = Decimal(str(rates.get(to_c, 1.0)))

        # Convert to base, then to target
        base_amount = amount / from_rate
        return (base_amount * to_rate).quantize(Decimal("0.01"))

    async def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Get exchange rate between two currencies."""
        rates = await self.fetch_rates()
        from_rate = Decimal(str(rates.get(from_currency.upper(), 1.0)))
        to_rate = Decimal(str(rates.get(to_currency.upper(), 1.0)))
        return (to_rate / from_rate).quantize(Decimal("0.000001"))

    def supported_currencies(self) -> list[str]:
        return sorted(self._rates.keys())


# Module-level singleton
fx_service = FXService()
