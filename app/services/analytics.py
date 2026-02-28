"""Sales analytics engine for cross-border e-commerce.

Provides daily/weekly/monthly aggregation, top-products ranking,
platform revenue breakdown, customer lifetime value, trend detection,
and simple revenue forecasting.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Sequence


class Period(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class Trend(str, Enum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class SalesMetric:
    """Single period metric snapshot."""
    period_start: date
    period_end: date
    order_count: int = 0
    item_count: int = 0
    gross_revenue: Decimal = Decimal("0")
    net_revenue: Decimal = Decimal("0")
    avg_order_value: Decimal = Decimal("0")
    refund_count: int = 0
    refund_amount: Decimal = Decimal("0")
    unique_customers: int = 0

    @property
    def refund_rate(self) -> Decimal:
        if self.order_count == 0:
            return Decimal("0")
        return (Decimal(self.refund_count) / Decimal(self.order_count) * 100).quantize(Decimal("0.01"))


@dataclass
class TopProduct:
    sku: str
    title: str
    units_sold: int
    revenue: Decimal
    order_count: int


@dataclass
class PlatformBreakdown:
    platform: str
    order_count: int
    revenue: Decimal
    share_pct: Decimal
    avg_order_value: Decimal


@dataclass
class CustomerValue:
    customer_id: str
    customer_name: str
    total_orders: int
    total_spent: Decimal
    first_order: date
    last_order: date
    avg_order_value: Decimal

    @property
    def lifetime_days(self) -> int:
        return max(1, (self.last_order - self.first_order).days)

    @property
    def frequency(self) -> Decimal:
        """Orders per 30 days."""
        if self.lifetime_days < 1:
            return Decimal(self.total_orders)
        return (Decimal(self.total_orders) / Decimal(self.lifetime_days) * 30).quantize(Decimal("0.01"))


@dataclass
class ForecastPoint:
    period: date
    predicted_revenue: Decimal
    confidence_low: Decimal
    confidence_high: Decimal


@dataclass
class TrendAnalysis:
    direction: Trend
    change_pct: Decimal
    current_value: Decimal
    previous_value: Decimal
    periods_analyzed: int


@dataclass
class AnalyticsReport:
    """Complete analytics report."""
    period: Period
    start_date: date
    end_date: date
    metrics: list[SalesMetric] = field(default_factory=list)
    top_products: list[TopProduct] = field(default_factory=list)
    platform_breakdown: list[PlatformBreakdown] = field(default_factory=list)
    revenue_trend: Optional[TrendAnalysis] = None
    order_trend: Optional[TrendAnalysis] = None
    forecast: list[ForecastPoint] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AnalyticsEngine:
    """Cross-border e-commerce analytics engine.

    Works with raw order/item dicts (no DB dependency) so it can be used
    as a pure calculation layer.
    """

    # ── Period Aggregation ──────────────────────────────

    @staticmethod
    def _period_key(dt: date, period: Period) -> date:
        if period == Period.DAILY:
            return dt
        elif period == Period.WEEKLY:
            return dt - timedelta(days=dt.weekday())  # Monday
        elif period == Period.MONTHLY:
            return dt.replace(day=1)
        elif period == Period.QUARTERLY:
            q = (dt.month - 1) // 3
            return dt.replace(month=q * 3 + 1, day=1)
        elif period == Period.YEARLY:
            return dt.replace(month=1, day=1)
        return dt

    @staticmethod
    def _period_end(start: date, period: Period) -> date:
        if period == Period.DAILY:
            return start
        elif period == Period.WEEKLY:
            return start + timedelta(days=6)
        elif period == Period.MONTHLY:
            if start.month == 12:
                return start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            return start.replace(month=start.month + 1, day=1) - timedelta(days=1)
        elif period == Period.QUARTERLY:
            end_month = start.month + 2
            if end_month > 12:
                end_month -= 12
                year = start.year + 1
            else:
                year = start.year
            if end_month == 12:
                return date(year, 12, 31)
            return date(year, end_month + 1, 1) - timedelta(days=1)
        elif period == Period.YEARLY:
            return date(start.year, 12, 31)
        return start

    def aggregate(
        self,
        orders: Sequence[dict],
        period: Period = Period.DAILY,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[SalesMetric]:
        """Aggregate orders into time-period buckets."""
        buckets: dict[date, dict] = defaultdict(lambda: {
            "orders": 0, "items": 0, "gross": Decimal("0"),
            "net": Decimal("0"), "refunds": 0, "refund_amt": Decimal("0"),
            "customers": set(),
        })

        for o in orders:
            odate = self._extract_date(o)
            if odate is None:
                continue
            if start_date and odate < start_date:
                continue
            if end_date and odate > end_date:
                continue

            key = self._period_key(odate, period)
            b = buckets[key]

            status = str(o.get("status", "")).lower()
            total = Decimal(str(o.get("total", 0)))

            if status == "refunded":
                b["refunds"] += 1
                b["refund_amt"] += total
            else:
                b["orders"] += 1
                b["gross"] += total
                b["net"] += total
                items = o.get("items", [])
                b["items"] += sum(int(i.get("quantity", 1)) for i in items) if items else 1

            cust = o.get("customer_email") or o.get("customer_name") or ""
            if cust:
                b["customers"].add(cust)

        metrics = []
        for pstart in sorted(buckets):
            b = buckets[pstart]
            pend = self._period_end(pstart, period)
            avg = (b["gross"] / b["orders"]).quantize(Decimal("0.01")) if b["orders"] else Decimal("0")
            metrics.append(SalesMetric(
                period_start=pstart,
                period_end=pend,
                order_count=b["orders"],
                item_count=b["items"],
                gross_revenue=b["gross"].quantize(Decimal("0.01")),
                net_revenue=(b["net"] - b["refund_amt"]).quantize(Decimal("0.01")),
                avg_order_value=avg,
                refund_count=b["refunds"],
                refund_amount=b["refund_amt"].quantize(Decimal("0.01")),
                unique_customers=len(b["customers"]),
            ))
        return metrics

    # ── Top Products ────────────────────────────────────

    def top_products(
        self,
        orders: Sequence[dict],
        limit: int = 10,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[TopProduct]:
        """Rank products by revenue."""
        products: dict[str, dict] = defaultdict(lambda: {
            "title": "", "units": 0, "revenue": Decimal("0"), "orders": set(),
        })

        for o in orders:
            odate = self._extract_date(o)
            if odate is None:
                continue
            if start_date and odate < start_date:
                continue
            if end_date and odate > end_date:
                continue
            status = str(o.get("status", "")).lower()
            if status in ("cancelled", "refunded"):
                continue

            oid = o.get("order_number", o.get("id", ""))
            for item in o.get("items", []):
                sku = item.get("sku", "unknown")
                p = products[sku]
                p["title"] = item.get("title", "") or p["title"]
                qty = int(item.get("quantity", 1))
                price = Decimal(str(item.get("total_price", item.get("unit_price", 0))))
                p["units"] += qty
                p["revenue"] += price * qty if price == Decimal(str(item.get("unit_price", 0))) else price
                p["orders"].add(oid)

        ranked = sorted(products.items(), key=lambda x: x[1]["revenue"], reverse=True)
        return [
            TopProduct(
                sku=sku,
                title=data["title"],
                units_sold=data["units"],
                revenue=data["revenue"].quantize(Decimal("0.01")),
                order_count=len(data["orders"]),
            )
            for sku, data in ranked[:limit]
        ]

    # ── Platform Breakdown ──────────────────────────────

    def platform_breakdown(
        self,
        orders: Sequence[dict],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[PlatformBreakdown]:
        """Revenue breakdown by platform."""
        platforms: dict[str, dict] = defaultdict(lambda: {
            "count": 0, "revenue": Decimal("0"),
        })
        total_revenue = Decimal("0")

        for o in orders:
            odate = self._extract_date(o)
            if odate is None:
                continue
            if start_date and odate < start_date:
                continue
            if end_date and odate > end_date:
                continue
            status = str(o.get("status", "")).lower()
            if status in ("cancelled", "refunded"):
                continue

            plat = str(o.get("platform", "unknown"))
            total = Decimal(str(o.get("total", 0)))
            platforms[plat]["count"] += 1
            platforms[plat]["revenue"] += total
            total_revenue += total

        result = []
        for plat, data in sorted(platforms.items(), key=lambda x: x[1]["revenue"], reverse=True):
            share = (data["revenue"] / total_revenue * 100).quantize(Decimal("0.01")) if total_revenue else Decimal("0")
            avg = (data["revenue"] / data["count"]).quantize(Decimal("0.01")) if data["count"] else Decimal("0")
            result.append(PlatformBreakdown(
                platform=plat,
                order_count=data["count"],
                revenue=data["revenue"].quantize(Decimal("0.01")),
                share_pct=share,
                avg_order_value=avg,
            ))
        return result

    # ── Customer Lifetime Value ─────────────────────────

    def customer_ltv(
        self,
        orders: Sequence[dict],
        limit: int = 20,
    ) -> list[CustomerValue]:
        """Calculate customer lifetime value, ranked by total spend."""
        customers: dict[str, dict] = defaultdict(lambda: {
            "name": "", "orders": 0, "spent": Decimal("0"),
            "first": date.max, "last": date.min,
        })

        for o in orders:
            odate = self._extract_date(o)
            if odate is None:
                continue
            status = str(o.get("status", "")).lower()
            if status in ("cancelled", "refunded"):
                continue

            cid = o.get("customer_email") or o.get("customer_name") or ""
            if not cid:
                continue
            c = customers[cid]
            c["name"] = o.get("customer_name", "") or c["name"]
            c["orders"] += 1
            c["spent"] += Decimal(str(o.get("total", 0)))
            if odate < c["first"]:
                c["first"] = odate
            if odate > c["last"]:
                c["last"] = odate

        ranked = sorted(customers.items(), key=lambda x: x[1]["spent"], reverse=True)
        result = []
        for cid, c in ranked[:limit]:
            avg = (c["spent"] / c["orders"]).quantize(Decimal("0.01")) if c["orders"] else Decimal("0")
            result.append(CustomerValue(
                customer_id=cid,
                customer_name=c["name"],
                total_orders=c["orders"],
                total_spent=c["spent"].quantize(Decimal("0.01")),
                first_order=c["first"],
                last_order=c["last"],
                avg_order_value=avg,
            ))
        return result

    # ── Trend Detection ─────────────────────────────────

    def detect_trend(
        self,
        metrics: Sequence[SalesMetric],
        field: str = "gross_revenue",
    ) -> TrendAnalysis:
        """Detect trend direction from a series of metrics."""
        values = [float(getattr(m, field, 0)) for m in metrics]
        if len(values) < 2:
            return TrendAnalysis(
                direction=Trend.STABLE,
                change_pct=Decimal("0"),
                current_value=Decimal(str(values[-1])) if values else Decimal("0"),
                previous_value=Decimal(str(values[0])) if values else Decimal("0"),
                periods_analyzed=len(values),
            )

        current = values[-1]
        previous = values[-2]

        if previous == 0:
            change = Decimal("100") if current > 0 else Decimal("0")
        else:
            change = Decimal(str(round((current - previous) / previous * 100, 2)))

        if change > 5:
            direction = Trend.RISING
        elif change < -5:
            direction = Trend.DECLINING
        else:
            direction = Trend.STABLE

        return TrendAnalysis(
            direction=direction,
            change_pct=change,
            current_value=Decimal(str(round(current, 2))),
            previous_value=Decimal(str(round(previous, 2))),
            periods_analyzed=len(values),
        )

    # ── Revenue Forecasting (Moving Average) ────────────

    def forecast(
        self,
        metrics: Sequence[SalesMetric],
        periods_ahead: int = 3,
        window: int = 4,
    ) -> list[ForecastPoint]:
        """Simple moving-average forecast with confidence bands."""
        values = [float(m.gross_revenue) for m in metrics]
        if len(values) < 2:
            return []

        # Moving average
        w = min(window, len(values))
        recent = values[-w:]
        ma = statistics.mean(recent)
        std = statistics.stdev(recent) if len(recent) >= 2 else ma * 0.1

        forecasts = []
        last_date = metrics[-1].period_end
        period_delta = (metrics[-1].period_start - metrics[-2].period_start).days or 1

        for i in range(1, periods_ahead + 1):
            future_date = last_date + timedelta(days=period_delta * i)
            predicted = Decimal(str(round(ma, 2)))
            margin = Decimal(str(round(std * 1.96, 2)))  # 95% CI
            forecasts.append(ForecastPoint(
                period=future_date,
                predicted_revenue=predicted,
                confidence_low=max(Decimal("0"), predicted - margin),
                confidence_high=predicted + margin,
            ))
        return forecasts

    # ── Full Report ─────────────────────────────────────

    def generate_report(
        self,
        orders: Sequence[dict],
        period: Period = Period.MONTHLY,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        top_n: int = 10,
        forecast_periods: int = 3,
    ) -> AnalyticsReport:
        """Generate a complete analytics report."""
        metrics = self.aggregate(orders, period, start_date, end_date)
        tops = self.top_products(orders, top_n, start_date, end_date)
        platforms = self.platform_breakdown(orders, start_date, end_date)

        rev_trend = self.detect_trend(metrics, "gross_revenue") if metrics else None
        ord_trend = self.detect_trend(metrics, "order_count") if metrics else None
        fc = self.forecast(metrics, forecast_periods) if len(metrics) >= 2 else []

        return AnalyticsReport(
            period=period,
            start_date=start_date or (metrics[0].period_start if metrics else date.today()),
            end_date=end_date or (metrics[-1].period_end if metrics else date.today()),
            metrics=metrics,
            top_products=tops,
            platform_breakdown=platforms,
            revenue_trend=rev_trend,
            order_trend=ord_trend,
            forecast=fc,
        )

    # ── Export ──────────────────────────────────────────

    def report_to_dict(self, report: AnalyticsReport) -> dict:
        """Convert report to JSON-serializable dict."""
        return {
            "period": report.period.value,
            "start_date": report.start_date.isoformat(),
            "end_date": report.end_date.isoformat(),
            "generated_at": report.generated_at.isoformat(),
            "summary": {
                "total_orders": sum(m.order_count for m in report.metrics),
                "total_revenue": str(sum(m.gross_revenue for m in report.metrics)),
                "total_refunds": sum(m.refund_count for m in report.metrics),
                "avg_order_value": str(
                    (sum(m.gross_revenue for m in report.metrics) /
                     max(1, sum(m.order_count for m in report.metrics))).quantize(Decimal("0.01"))
                ),
            },
            "metrics": [
                {
                    "period_start": m.period_start.isoformat(),
                    "period_end": m.period_end.isoformat(),
                    "order_count": m.order_count,
                    "gross_revenue": str(m.gross_revenue),
                    "net_revenue": str(m.net_revenue),
                    "avg_order_value": str(m.avg_order_value),
                    "refund_count": m.refund_count,
                    "unique_customers": m.unique_customers,
                }
                for m in report.metrics
            ],
            "top_products": [
                {
                    "sku": tp.sku,
                    "title": tp.title,
                    "units_sold": tp.units_sold,
                    "revenue": str(tp.revenue),
                }
                for tp in report.top_products
            ],
            "platform_breakdown": [
                {
                    "platform": pb.platform,
                    "order_count": pb.order_count,
                    "revenue": str(pb.revenue),
                    "share_pct": str(pb.share_pct),
                }
                for pb in report.platform_breakdown
            ],
            "revenue_trend": {
                "direction": report.revenue_trend.direction.value,
                "change_pct": str(report.revenue_trend.change_pct),
            } if report.revenue_trend else None,
            "forecast": [
                {
                    "period": fp.period.isoformat(),
                    "predicted": str(fp.predicted_revenue),
                    "low": str(fp.confidence_low),
                    "high": str(fp.confidence_high),
                }
                for fp in report.forecast
            ],
        }

    # ── Helpers ─────────────────────────────────────────

    @staticmethod
    def _extract_date(order: dict) -> Optional[date]:
        """Extract date from an order dict (supports multiple key names)."""
        for key in ("created_at", "ordered_at", "date", "order_date"):
            val = order.get(key)
            if val is None:
                continue
            if isinstance(val, datetime):
                return val.date()
            if isinstance(val, date):
                return val
            if isinstance(val, str):
                try:
                    return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
                except (ValueError, TypeError):
                    continue
        return None
