"""Profit and margin calculation service for cross-border products."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a product."""
    product_cost: Decimal = Decimal("0")          # 采购成本 (CNY)
    shipping_domestic: Decimal = Decimal("0")     # 国内运费
    shipping_intl: Decimal = Decimal("0")         # 国际运费
    platform_fee_pct: Decimal = Decimal("15")     # 平台佣金 %
    ad_cost: Decimal = Decimal("0")               # 广告成本
    packaging: Decimal = Decimal("0.50")          # 包装成本
    fba_fee: Decimal = Decimal("0")               # FBA费用
    customs_duty_pct: Decimal = Decimal("0")      # 关税 %
    vat_pct: Decimal = Decimal("0")               # 增值税 %
    fx_rate: Decimal = Decimal("7.25")            # CNY/USD汇率
    return_rate_pct: Decimal = Decimal("3")       # 退货率 %


@dataclass
class ProfitReport:
    """Profit analysis result."""
    selling_price: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    gross_margin_pct: Decimal
    net_profit: Decimal
    net_margin_pct: Decimal
    roi_pct: Decimal
    break_even_price: Decimal
    cost_details: dict = field(default_factory=dict)

    @property
    def is_profitable(self) -> bool:
        return self.net_profit > 0


class ProfitCalculator:
    """Cross-border e-commerce profit calculator."""

    @staticmethod
    def calculate(
        selling_price_usd: Decimal,
        costs: CostBreakdown,
    ) -> ProfitReport:
        """Calculate profit for a single product sale."""
        sp = selling_price_usd

        # Convert CNY costs to USD
        product_cost_usd = costs.product_cost / costs.fx_rate
        domestic_ship_usd = costs.shipping_domestic / costs.fx_rate
        packaging_usd = costs.packaging / costs.fx_rate

        # Platform fee
        platform_fee = sp * (costs.platform_fee_pct / Decimal("100"))

        # Customs & VAT
        customs = product_cost_usd * (costs.customs_duty_pct / Decimal("100"))
        vat = sp * (costs.vat_pct / Decimal("100"))

        # Return cost (fraction of selling price)
        return_cost = sp * (costs.return_rate_pct / Decimal("100"))

        # Total cost of goods
        cogs = product_cost_usd + domestic_ship_usd + packaging_usd

        # Total cost
        total_cost = (
            cogs
            + costs.shipping_intl
            + platform_fee
            + costs.ad_cost
            + costs.fba_fee
            + customs
            + vat
            + return_cost
        )

        gross_profit = sp - cogs - costs.shipping_intl
        net_profit = sp - total_cost

        gross_margin = (gross_profit / sp * 100).quantize(Decimal("0.01")) if sp else Decimal("0")
        net_margin = (net_profit / sp * 100).quantize(Decimal("0.01")) if sp else Decimal("0")
        roi = (net_profit / total_cost * 100).quantize(Decimal("0.01")) if total_cost else Decimal("0")

        # Break-even price
        break_even = total_cost / (1 - costs.platform_fee_pct / 100 - costs.return_rate_pct / 100)

        cost_details = {
            "product_cost_usd": product_cost_usd.quantize(Decimal("0.01")),
            "domestic_shipping_usd": domestic_ship_usd.quantize(Decimal("0.01")),
            "intl_shipping_usd": costs.shipping_intl,
            "platform_fee_usd": platform_fee.quantize(Decimal("0.01")),
            "ad_cost_usd": costs.ad_cost,
            "fba_fee_usd": costs.fba_fee,
            "packaging_usd": packaging_usd.quantize(Decimal("0.01")),
            "customs_usd": customs.quantize(Decimal("0.01")),
            "vat_usd": vat.quantize(Decimal("0.01")),
            "return_cost_usd": return_cost.quantize(Decimal("0.01")),
        }

        return ProfitReport(
            selling_price=sp.quantize(Decimal("0.01")),
            total_cost=total_cost.quantize(Decimal("0.01")),
            gross_profit=gross_profit.quantize(Decimal("0.01")),
            gross_margin_pct=gross_margin,
            net_profit=net_profit.quantize(Decimal("0.01")),
            net_margin_pct=net_margin,
            roi_pct=roi,
            break_even_price=break_even.quantize(Decimal("0.01")),
            cost_details=cost_details,
        )

    @staticmethod
    def batch_calculate(
        products: list[dict],
        default_costs: Optional[CostBreakdown] = None,
    ) -> list[ProfitReport]:
        """Calculate profit for multiple products."""
        results = []
        dc = default_costs or CostBreakdown()
        for p in products:
            costs = CostBreakdown(
                product_cost=Decimal(str(p.get("cost_price", dc.product_cost))),
                shipping_intl=Decimal(str(p.get("shipping_intl", dc.shipping_intl))),
                platform_fee_pct=Decimal(str(p.get("platform_fee_pct", dc.platform_fee_pct))),
                ad_cost=Decimal(str(p.get("ad_cost", dc.ad_cost))),
                fba_fee=Decimal(str(p.get("fba_fee", dc.fba_fee))),
                fx_rate=dc.fx_rate,
                return_rate_pct=dc.return_rate_pct,
            )
            report = ProfitCalculator.calculate(
                Decimal(str(p.get("selling_price", "0"))),
                costs,
            )
            results.append(report)
        return results
