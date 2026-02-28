"""Reports & Analytics API — profit reports, sales trends, inventory health."""

from decimal import Decimal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Order, OrderItem, Product, InventoryItem, Supplier
from app.services.profit_calc import ProfitCalculator, CostBreakdown

router = APIRouter(prefix="/reports", tags=["reports"])


class ProfitReportOut(BaseModel):
    sku: str
    title: str
    selling_price: float
    total_cost: float
    net_profit: float
    net_margin_pct: float
    roi_pct: float
    is_profitable: bool


class SalesTrend(BaseModel):
    period: str
    order_count: int
    revenue: float
    avg_order_value: float


class InventoryHealthItem(BaseModel):
    sku: str
    title: str
    warehouse: str
    quantity: int
    reserved: int
    available: int
    threshold: int
    status: str  # ok / low / critical / out_of_stock


class OverviewReport(BaseModel):
    total_revenue: float
    total_orders: int
    avg_order_value: float
    total_products: int
    active_products: int
    low_stock_count: int
    out_of_stock_count: int
    total_suppliers: int
    top_products: list[dict]
    platform_breakdown: list[dict]


@router.get("/profit", response_model=list[ProfitReportOut])
async def profit_report(
    platform_fee_pct: float = Query(15.0, description="Platform commission %"),
    fx_rate: float = Query(7.25, description="CNY/USD exchange rate"),
    db: AsyncSession = Depends(get_db),
):
    """Calculate profit for all active products."""
    result = await db.execute(
        select(Product).where(Product.active.is_(True)).order_by(Product.sku)
    )
    products = result.scalars().all()

    reports = []
    for p in products:
        if not p.retail_price or p.retail_price <= 0:
            continue
        costs = CostBreakdown(
            product_cost=p.cost_price or Decimal("0"),
            platform_fee_pct=Decimal(str(platform_fee_pct)),
            fx_rate=Decimal(str(fx_rate)),
        )
        report = ProfitCalculator.calculate(p.retail_price, costs)
        reports.append(ProfitReportOut(
            sku=p.sku,
            title=p.title,
            selling_price=float(report.selling_price),
            total_cost=float(report.total_cost),
            net_profit=float(report.net_profit),
            net_margin_pct=float(report.net_margin_pct),
            roi_pct=float(report.roi_pct),
            is_profitable=report.is_profitable,
        ))

    return reports


@router.get("/sales-trends", response_model=list[SalesTrend])
async def sales_trends(
    months: int = Query(6, ge=1, le=24, description="Number of months to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly sales trends."""
    stmt = (
        select(
            extract("year", Order.created_at).label("year"),
            extract("month", Order.created_at).label("month"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total), 0).label("revenue"),
        )
        .group_by("year", "month")
        .order_by("year", "month")
        .limit(months)
    )
    result = await db.execute(stmt)
    rows = result.all()

    trends = []
    for row in rows:
        count = int(row.order_count)
        rev = float(row.revenue)
        trends.append(SalesTrend(
            period=f"{int(row.year)}-{int(row.month):02d}",
            order_count=count,
            revenue=round(rev, 2),
            avg_order_value=round(rev / count, 2) if count > 0 else 0.0,
        ))
    return trends


@router.get("/inventory-health", response_model=list[InventoryHealthItem])
async def inventory_health(db: AsyncSession = Depends(get_db)):
    """Check inventory health across all warehouses."""
    stmt = (
        select(InventoryItem, Product)
        .join(Product, InventoryItem.product_id == Product.id)
        .order_by(InventoryItem.quantity.asc())
    )
    result = await db.execute(stmt)
    items = result.all()

    health = []
    for inv, prod in items:
        available = max(0, inv.quantity - inv.reserved)
        if available == 0:
            status = "out_of_stock"
        elif available <= inv.low_stock_threshold // 2:
            status = "critical"
        elif available <= inv.low_stock_threshold:
            status = "low"
        else:
            status = "ok"

        health.append(InventoryHealthItem(
            sku=prod.sku,
            title=prod.title,
            warehouse=inv.warehouse,
            quantity=inv.quantity,
            reserved=inv.reserved,
            available=available,
            threshold=inv.low_stock_threshold,
            status=status,
        ))
    return health


@router.get("/overview", response_model=OverviewReport)
async def overview_report(db: AsyncSession = Depends(get_db)):
    """Comprehensive business overview report."""
    # Revenue & orders
    total_rev = (
        await db.execute(select(func.coalesce(func.sum(Order.total), 0)))
    ).scalar() or 0
    total_orders = (
        await db.execute(select(func.count(Order.id)))
    ).scalar() or 0

    avg_order = float(total_rev) / total_orders if total_orders > 0 else 0.0

    # Products
    total_products = (await db.execute(select(func.count(Product.id)))).scalar() or 0
    active_products = (
        await db.execute(select(func.count(Product.id)).where(Product.active.is_(True)))
    ).scalar() or 0

    # Inventory
    low_stock = (
        await db.execute(
            select(func.count(InventoryItem.id)).where(
                (InventoryItem.quantity - InventoryItem.reserved) <= InventoryItem.low_stock_threshold,
                (InventoryItem.quantity - InventoryItem.reserved) > 0,
            )
        )
    ).scalar() or 0

    out_of_stock = (
        await db.execute(
            select(func.count(InventoryItem.id)).where(
                (InventoryItem.quantity - InventoryItem.reserved) <= 0
            )
        )
    ).scalar() or 0

    # Suppliers
    total_suppliers = (await db.execute(select(func.count(Supplier.id)))).scalar() or 0

    # Top products by order count
    top_stmt = (
        select(
            OrderItem.sku,
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.total_price).label("total_revenue"),
        )
        .group_by(OrderItem.sku)
        .order_by(func.sum(OrderItem.total_price).desc())
        .limit(10)
    )
    top_result = await db.execute(top_stmt)
    top_products = [
        {"sku": r.sku, "total_qty": int(r.total_qty), "revenue": float(r.total_revenue)}
        for r in top_result.all()
    ]

    # Platform breakdown
    platform_stmt = (
        select(
            Order.platform,
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total), 0).label("revenue"),
        )
        .group_by(Order.platform)
        .order_by(func.sum(Order.total).desc())
    )
    platform_result = await db.execute(platform_stmt)
    platform_breakdown = [
        {
            "platform": r.platform.value if hasattr(r.platform, "value") else str(r.platform),
            "orders": int(r.orders),
            "revenue": float(r.revenue),
        }
        for r in platform_result.all()
    ]

    return OverviewReport(
        total_revenue=round(float(total_rev), 2),
        total_orders=total_orders,
        avg_order_value=round(avg_order, 2),
        total_products=total_products,
        active_products=active_products,
        low_stock_count=low_stock,
        out_of_stock_count=out_of_stock,
        total_suppliers=total_suppliers,
        top_products=top_products,
        platform_breakdown=platform_breakdown,
    )
