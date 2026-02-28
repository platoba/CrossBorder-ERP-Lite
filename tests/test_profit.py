"""Profit calculator tests."""

import pytest
from decimal import Decimal

from app.services.profit_calc import CostBreakdown, ProfitCalculator, ProfitReport


class TestProfitCalculator:
    def test_basic_profit(self):
        costs = CostBreakdown(
            product_cost=Decimal("50"),  # 50 CNY
            fx_rate=Decimal("7.25"),
        )
        report = ProfitCalculator.calculate(Decimal("19.99"), costs)
        assert isinstance(report, ProfitReport)
        assert report.selling_price == Decimal("19.99")
        assert report.is_profitable

    def test_unprofitable_product(self):
        costs = CostBreakdown(
            product_cost=Decimal("200"),  # High cost
            shipping_intl=Decimal("10"),
            platform_fee_pct=Decimal("20"),
            fx_rate=Decimal("7.25"),
        )
        report = ProfitCalculator.calculate(Decimal("9.99"), costs)
        assert not report.is_profitable
        assert report.net_profit < 0

    def test_with_fba_fee(self):
        costs = CostBreakdown(
            product_cost=Decimal("30"),
            fba_fee=Decimal("5.50"),
            fx_rate=Decimal("7.25"),
        )
        report = ProfitCalculator.calculate(Decimal("25.00"), costs)
        assert report.cost_details["fba_fee_usd"] == Decimal("5.50")

    def test_with_customs_and_vat(self):
        costs = CostBreakdown(
            product_cost=Decimal("100"),
            customs_duty_pct=Decimal("10"),
            vat_pct=Decimal("20"),
            fx_rate=Decimal("7.25"),
        )
        report = ProfitCalculator.calculate(Decimal("50.00"), costs)
        assert float(report.cost_details["customs_usd"]) > 0
        assert float(report.cost_details["vat_usd"]) > 0

    def test_return_cost_included(self):
        costs = CostBreakdown(
            product_cost=Decimal("20"),
            return_rate_pct=Decimal("5"),
            fx_rate=Decimal("7.25"),
        )
        report = ProfitCalculator.calculate(Decimal("30.00"), costs)
        assert float(report.cost_details["return_cost_usd"]) == 1.50  # 5% of 30

    def test_zero_selling_price(self):
        costs = CostBreakdown(product_cost=Decimal("10"))
        report = ProfitCalculator.calculate(Decimal("0"), costs)
        assert report.gross_margin_pct == Decimal("0")
        assert report.net_margin_pct == Decimal("0")

    def test_batch_calculate(self):
        products = [
            {"cost_price": 30, "selling_price": 19.99},
            {"cost_price": 50, "selling_price": 29.99},
            {"cost_price": 100, "selling_price": 49.99},
        ]
        reports = ProfitCalculator.batch_calculate(products)
        assert len(reports) == 3
        assert all(isinstance(r, ProfitReport) for r in reports)

    def test_roi_calculation(self):
        costs = CostBreakdown(
            product_cost=Decimal("50"),
            fx_rate=Decimal("7.25"),
            platform_fee_pct=Decimal("15"),
        )
        report = ProfitCalculator.calculate(Decimal("30.00"), costs)
        assert report.roi_pct != Decimal("0")

    def test_break_even_price(self):
        costs = CostBreakdown(
            product_cost=Decimal("72.5"),  # 10 USD at 7.25 rate
            fx_rate=Decimal("7.25"),
            platform_fee_pct=Decimal("15"),
            return_rate_pct=Decimal("3"),
        )
        report = ProfitCalculator.calculate(Decimal("20.00"), costs)
        assert report.break_even_price > Decimal("0")
