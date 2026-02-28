"""Tests for the analytics engine."""

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal

from app.services.analytics import (
    AnalyticsEngine, AnalyticsReport, CustomerValue, ForecastPoint,
    Period, PlatformBreakdown, SalesMetric, TopProduct, Trend, TrendAnalysis,
)


# ── Fixtures ────────────────────────────────────────────

@pytest.fixture
def engine():
    return AnalyticsEngine()


@pytest.fixture
def sample_orders():
    """Multi-platform, multi-date order set."""
    return [
        {
            "order_number": "ORD-001",
            "platform": "amazon",
            "status": "delivered",
            "total": "29.99",
            "customer_name": "Alice",
            "customer_email": "alice@test.com",
            "created_at": "2026-01-05T10:00:00Z",
            "items": [
                {"sku": "SKU-A", "title": "Widget A", "quantity": 2, "unit_price": "10.00", "total_price": "20.00"},
                {"sku": "SKU-B", "title": "Widget B", "quantity": 1, "unit_price": "9.99", "total_price": "9.99"},
            ],
        },
        {
            "order_number": "ORD-002",
            "platform": "shopify",
            "status": "shipped",
            "total": "49.98",
            "customer_name": "Bob",
            "customer_email": "bob@test.com",
            "created_at": "2026-01-12T14:00:00Z",
            "items": [
                {"sku": "SKU-A", "title": "Widget A", "quantity": 3, "unit_price": "10.00", "total_price": "30.00"},
                {"sku": "SKU-C", "title": "Gadget C", "quantity": 1, "unit_price": "19.98", "total_price": "19.98"},
            ],
        },
        {
            "order_number": "ORD-003",
            "platform": "amazon",
            "status": "delivered",
            "total": "15.00",
            "customer_name": "Alice",
            "customer_email": "alice@test.com",
            "created_at": "2026-02-03T09:00:00Z",
            "items": [
                {"sku": "SKU-B", "title": "Widget B", "quantity": 1, "unit_price": "15.00", "total_price": "15.00"},
            ],
        },
        {
            "order_number": "ORD-004",
            "platform": "ebay",
            "status": "refunded",
            "total": "20.00",
            "customer_name": "Charlie",
            "customer_email": "charlie@test.com",
            "created_at": "2026-02-10T11:00:00Z",
            "items": [],
        },
        {
            "order_number": "ORD-005",
            "platform": "amazon",
            "status": "delivered",
            "total": "99.99",
            "customer_name": "Diana",
            "customer_email": "diana@test.com",
            "created_at": "2026-03-01T16:00:00Z",
            "items": [
                {"sku": "SKU-A", "title": "Widget A", "quantity": 5, "unit_price": "10.00", "total_price": "50.00"},
                {"sku": "SKU-D", "title": "Pro Gadget", "quantity": 1, "unit_price": "49.99", "total_price": "49.99"},
            ],
        },
    ]


# ── Period Key ──────────────────────────────────────────

class TestPeriodKey:
    def test_daily(self, engine):
        assert engine._period_key(date(2026, 1, 15), Period.DAILY) == date(2026, 1, 15)

    def test_weekly(self, engine):
        # 2026-01-15 is Thursday → Monday is 2026-01-12
        key = engine._period_key(date(2026, 1, 15), Period.WEEKLY)
        assert key == date(2026, 1, 12)

    def test_monthly(self, engine):
        assert engine._period_key(date(2026, 3, 25), Period.MONTHLY) == date(2026, 3, 1)

    def test_quarterly(self, engine):
        assert engine._period_key(date(2026, 5, 15), Period.QUARTERLY) == date(2026, 4, 1)
        assert engine._period_key(date(2026, 11, 1), Period.QUARTERLY) == date(2026, 10, 1)

    def test_yearly(self, engine):
        assert engine._period_key(date(2026, 7, 4), Period.YEARLY) == date(2026, 1, 1)


class TestPeriodEnd:
    def test_daily(self, engine):
        assert engine._period_end(date(2026, 1, 15), Period.DAILY) == date(2026, 1, 15)

    def test_weekly(self, engine):
        assert engine._period_end(date(2026, 1, 12), Period.WEEKLY) == date(2026, 1, 18)

    def test_monthly(self, engine):
        assert engine._period_end(date(2026, 1, 1), Period.MONTHLY) == date(2026, 1, 31)
        assert engine._period_end(date(2026, 2, 1), Period.MONTHLY) == date(2026, 2, 28)

    def test_monthly_dec(self, engine):
        assert engine._period_end(date(2026, 12, 1), Period.MONTHLY) == date(2026, 12, 31)

    def test_yearly(self, engine):
        assert engine._period_end(date(2026, 1, 1), Period.YEARLY) == date(2026, 12, 31)


# ── Aggregation ─────────────────────────────────────────

class TestAggregate:
    def test_monthly_aggregation(self, engine, sample_orders):
        metrics = engine.aggregate(sample_orders, Period.MONTHLY)
        assert len(metrics) == 3  # Jan, Feb, Mar

    def test_jan_metrics(self, engine, sample_orders):
        metrics = engine.aggregate(sample_orders, Period.MONTHLY)
        jan = metrics[0]
        assert jan.period_start == date(2026, 1, 1)
        assert jan.order_count == 2
        assert jan.gross_revenue == Decimal("79.97")

    def test_refund_counted(self, engine, sample_orders):
        metrics = engine.aggregate(sample_orders, Period.MONTHLY)
        feb = metrics[1]
        assert feb.refund_count == 1
        assert feb.refund_amount == Decimal("20.00")

    def test_date_filter(self, engine, sample_orders):
        metrics = engine.aggregate(
            sample_orders, Period.MONTHLY,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 28),
        )
        assert len(metrics) == 1
        assert metrics[0].period_start == date(2026, 2, 1)

    def test_avg_order_value(self, engine, sample_orders):
        metrics = engine.aggregate(sample_orders, Period.MONTHLY)
        jan = metrics[0]
        expected_avg = (Decimal("79.97") / 2).quantize(Decimal("0.01"))
        assert jan.avg_order_value == expected_avg

    def test_unique_customers(self, engine, sample_orders):
        metrics = engine.aggregate(sample_orders, Period.MONTHLY)
        jan = metrics[0]
        assert jan.unique_customers == 2  # Alice and Bob

    def test_empty_orders(self, engine):
        metrics = engine.aggregate([], Period.MONTHLY)
        assert metrics == []

    def test_daily_aggregation(self, engine, sample_orders):
        metrics = engine.aggregate(sample_orders, Period.DAILY)
        assert len(metrics) >= 4  # At least 4 different dates

    def test_item_count(self, engine, sample_orders):
        metrics = engine.aggregate(sample_orders, Period.MONTHLY)
        jan = metrics[0]
        # ORD-001: 2+1=3, ORD-002: 3+1=4 → 7
        assert jan.item_count == 7


# ── Sales Metric ────────────────────────────────────────

class TestSalesMetric:
    def test_refund_rate_zero(self):
        m = SalesMetric(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        assert m.refund_rate == Decimal("0")

    def test_refund_rate_calculated(self):
        m = SalesMetric(
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            order_count=10, refund_count=2,
        )
        assert m.refund_rate == Decimal("20.00")


# ── Top Products ────────────────────────────────────────

class TestTopProducts:
    def test_ranking(self, engine, sample_orders):
        tops = engine.top_products(sample_orders)
        assert len(tops) >= 1
        # SKU-A should be top (highest revenue)
        assert tops[0].sku == "SKU-A"

    def test_limit(self, engine, sample_orders):
        tops = engine.top_products(sample_orders, limit=2)
        assert len(tops) == 2

    def test_units_counted(self, engine, sample_orders):
        tops = engine.top_products(sample_orders)
        sku_a = next(t for t in tops if t.sku == "SKU-A")
        assert sku_a.units_sold == 10  # 2+3+5

    def test_cancelled_excluded(self, engine):
        orders = [
            {
                "order_number": "X1", "platform": "amazon", "status": "cancelled",
                "total": "100", "created_at": "2026-01-01",
                "items": [{"sku": "SKU-X", "title": "Cancelled", "quantity": 5, "unit_price": "20", "total_price": "100"}],
            },
            {
                "order_number": "X2", "platform": "amazon", "status": "delivered",
                "total": "10", "created_at": "2026-01-01",
                "items": [{"sku": "SKU-Y", "title": "Good", "quantity": 1, "unit_price": "10", "total_price": "10"}],
            },
        ]
        tops = engine.top_products(orders)
        skus = [t.sku for t in tops]
        assert "SKU-X" not in skus
        assert "SKU-Y" in skus

    def test_date_filter(self, engine, sample_orders):
        tops = engine.top_products(
            sample_orders,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )
        # Only March orders
        skus = [t.sku for t in tops]
        assert "SKU-D" in skus


# ── Platform Breakdown ──────────────────────────────────

class TestPlatformBreakdown:
    def test_platforms_present(self, engine, sample_orders):
        breakdown = engine.platform_breakdown(sample_orders)
        platforms = [pb.platform for pb in breakdown]
        assert "amazon" in platforms
        assert "shopify" in platforms

    def test_refunded_excluded(self, engine, sample_orders):
        breakdown = engine.platform_breakdown(sample_orders)
        # ebay order was refunded, should be excluded
        ebay = [pb for pb in breakdown if pb.platform == "ebay"]
        assert len(ebay) == 0

    def test_share_adds_to_100(self, engine, sample_orders):
        breakdown = engine.platform_breakdown(sample_orders)
        total_share = sum(pb.share_pct for pb in breakdown)
        assert abs(total_share - Decimal("100")) < Decimal("0.1")

    def test_revenue_correct(self, engine, sample_orders):
        breakdown = engine.platform_breakdown(sample_orders)
        amazon = next(pb for pb in breakdown if pb.platform == "amazon")
        # ORD-001(29.99) + ORD-003(15.00) + ORD-005(99.99) = 144.98
        assert amazon.revenue == Decimal("144.98")


# ── Customer LTV ────────────────────────────────────────

class TestCustomerLTV:
    def test_ranking(self, engine, sample_orders):
        customers = engine.customer_ltv(sample_orders)
        assert len(customers) >= 1

    def test_alice_repeat(self, engine, sample_orders):
        customers = engine.customer_ltv(sample_orders)
        alice = next(c for c in customers if "alice" in c.customer_id.lower())
        assert alice.total_orders == 2

    def test_frequency(self, engine, sample_orders):
        customers = engine.customer_ltv(sample_orders)
        alice = next(c for c in customers if "alice" in c.customer_id.lower())
        assert alice.frequency > 0

    def test_lifetime_days(self):
        cv = CustomerValue(
            customer_id="test", customer_name="Test",
            total_orders=3, total_spent=Decimal("100"),
            first_order=date(2026, 1, 1), last_order=date(2026, 3, 1),
            avg_order_value=Decimal("33.33"),
        )
        assert cv.lifetime_days == 59


# ── Trend Detection ─────────────────────────────────────

class TestTrendDetection:
    def test_rising(self, engine):
        metrics = [
            SalesMetric(date(2026, 1, 1), date(2026, 1, 31), gross_revenue=Decimal("100")),
            SalesMetric(date(2026, 2, 1), date(2026, 2, 28), gross_revenue=Decimal("150")),
        ]
        trend = engine.detect_trend(metrics)
        assert trend.direction == Trend.RISING
        assert trend.change_pct == Decimal("50.00")

    def test_declining(self, engine):
        metrics = [
            SalesMetric(date(2026, 1, 1), date(2026, 1, 31), gross_revenue=Decimal("200")),
            SalesMetric(date(2026, 2, 1), date(2026, 2, 28), gross_revenue=Decimal("100")),
        ]
        trend = engine.detect_trend(metrics)
        assert trend.direction == Trend.DECLINING

    def test_stable(self, engine):
        metrics = [
            SalesMetric(date(2026, 1, 1), date(2026, 1, 31), gross_revenue=Decimal("100")),
            SalesMetric(date(2026, 2, 1), date(2026, 2, 28), gross_revenue=Decimal("102")),
        ]
        trend = engine.detect_trend(metrics)
        assert trend.direction == Trend.STABLE

    def test_single_period(self, engine):
        metrics = [SalesMetric(date(2026, 1, 1), date(2026, 1, 31), gross_revenue=Decimal("100"))]
        trend = engine.detect_trend(metrics)
        assert trend.direction == Trend.STABLE
        assert trend.periods_analyzed == 1

    def test_from_zero(self, engine):
        metrics = [
            SalesMetric(date(2026, 1, 1), date(2026, 1, 31), gross_revenue=Decimal("0")),
            SalesMetric(date(2026, 2, 1), date(2026, 2, 28), gross_revenue=Decimal("100")),
        ]
        trend = engine.detect_trend(metrics)
        assert trend.direction == Trend.RISING


# ── Forecasting ─────────────────────────────────────────

class TestForecasting:
    def test_basic_forecast(self, engine):
        metrics = [
            SalesMetric(date(2026, 1, 1), date(2026, 1, 31), gross_revenue=Decimal("100")),
            SalesMetric(date(2026, 2, 1), date(2026, 2, 28), gross_revenue=Decimal("120")),
            SalesMetric(date(2026, 3, 1), date(2026, 3, 31), gross_revenue=Decimal("110")),
        ]
        fc = engine.forecast(metrics, periods_ahead=2)
        assert len(fc) == 2
        assert fc[0].predicted_revenue > 0
        assert fc[0].confidence_low <= fc[0].predicted_revenue
        assert fc[0].confidence_high >= fc[0].predicted_revenue

    def test_single_period_no_forecast(self, engine):
        metrics = [SalesMetric(date(2026, 1, 1), date(2026, 1, 31), gross_revenue=Decimal("100"))]
        fc = engine.forecast(metrics)
        assert fc == []

    def test_confidence_band(self, engine):
        metrics = [
            SalesMetric(date(2026, i, 1), date(2026, i, 28), gross_revenue=Decimal(str(100 + i * 10)))
            for i in range(1, 7)
        ]
        fc = engine.forecast(metrics, periods_ahead=1)
        assert fc[0].confidence_low >= 0


# ── Full Report ─────────────────────────────────────────

class TestFullReport:
    def test_report_structure(self, engine, sample_orders):
        report = engine.generate_report(sample_orders)
        assert isinstance(report, AnalyticsReport)
        assert len(report.metrics) > 0
        assert len(report.top_products) > 0
        assert len(report.platform_breakdown) > 0
        assert report.revenue_trend is not None

    def test_report_to_dict(self, engine, sample_orders):
        report = engine.generate_report(sample_orders)
        d = engine.report_to_dict(report)
        assert "summary" in d
        assert "metrics" in d
        assert "top_products" in d
        assert "platform_breakdown" in d
        assert "revenue_trend" in d
        assert "forecast" in d

    def test_report_summary_totals(self, engine, sample_orders):
        report = engine.generate_report(sample_orders)
        d = engine.report_to_dict(report)
        assert int(d["summary"]["total_orders"]) >= 3


# ── Date Extraction ─────────────────────────────────────

class TestDateExtraction:
    def test_iso_string(self, engine):
        d = engine._extract_date({"created_at": "2026-01-15T10:00:00Z"})
        assert d == date(2026, 1, 15)

    def test_datetime_obj(self, engine):
        dt = datetime(2026, 3, 10, 8, 0, 0, tzinfo=timezone.utc)
        d = engine._extract_date({"created_at": dt})
        assert d == date(2026, 3, 10)

    def test_date_obj(self, engine):
        d = engine._extract_date({"created_at": date(2026, 5, 1)})
        assert d == date(2026, 5, 1)

    def test_fallback_keys(self, engine):
        d = engine._extract_date({"order_date": "2026-06-01"})
        assert d == date(2026, 6, 1)

    def test_missing_returns_none(self, engine):
        assert engine._extract_date({}) is None

    def test_invalid_returns_none(self, engine):
        assert engine._extract_date({"created_at": "not-a-date"}) is None
