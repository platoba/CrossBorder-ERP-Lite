"""Analytics API endpoints."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.services.analytics import AnalyticsEngine, Period

router = APIRouter(prefix="/analytics", tags=["analytics"])
engine = AnalyticsEngine()

# In a real app, orders come from the database.
# Here we define the endpoints and accept orders as POST body for demo.


@router.post("/report")
async def generate_report(
    orders: list[dict],
    period: Period = Query(Period.MONTHLY, description="Aggregation period"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    top_n: int = Query(10, ge=1, le=100),
    forecast_periods: int = Query(3, ge=0, le=12),
):
    """Generate a full analytics report from order data."""
    report = engine.generate_report(
        orders=orders,
        period=period,
        start_date=start_date,
        end_date=end_date,
        top_n=top_n,
        forecast_periods=forecast_periods,
    )
    return engine.report_to_dict(report)


@router.post("/top-products")
async def top_products(
    orders: list[dict],
    limit: int = Query(10, ge=1, le=100),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get top-selling products ranked by revenue."""
    tops = engine.top_products(orders, limit, start_date, end_date)
    return [
        {
            "sku": tp.sku,
            "title": tp.title,
            "units_sold": tp.units_sold,
            "revenue": str(tp.revenue),
            "order_count": tp.order_count,
        }
        for tp in tops
    ]


@router.post("/platform-breakdown")
async def platform_breakdown(
    orders: list[dict],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Revenue breakdown by platform."""
    breakdown = engine.platform_breakdown(orders, start_date, end_date)
    return [
        {
            "platform": pb.platform,
            "order_count": pb.order_count,
            "revenue": str(pb.revenue),
            "share_pct": str(pb.share_pct),
            "avg_order_value": str(pb.avg_order_value),
        }
        for pb in breakdown
    ]


@router.post("/customer-ltv")
async def customer_ltv(
    orders: list[dict],
    limit: int = Query(20, ge=1, le=100),
):
    """Customer lifetime value ranking."""
    customers = engine.customer_ltv(orders, limit)
    return [
        {
            "customer_id": cv.customer_id,
            "customer_name": cv.customer_name,
            "total_orders": cv.total_orders,
            "total_spent": str(cv.total_spent),
            "avg_order_value": str(cv.avg_order_value),
            "frequency_per_30d": str(cv.frequency),
            "lifetime_days": cv.lifetime_days,
        }
        for cv in customers
    ]
