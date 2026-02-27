"""Dashboard stats API."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import InventoryItem, Order, Product, Supplier
from app.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_products = (await db.execute(select(func.count(Product.id)))).scalar() or 0
    active_products = (
        await db.execute(select(func.count(Product.id)).where(Product.active.is_(True)))
    ).scalar() or 0

    total_orders = (await db.execute(select(func.count(Order.id)))).scalar() or 0
    pending_orders = (
        await db.execute(select(func.count(Order.id)).where(Order.status == "pending"))
    ).scalar() or 0

    total_revenue = (
        await db.execute(select(func.coalesce(func.sum(Order.total), 0)))
    ).scalar() or Decimal("0")

    # Low stock count
    low_stock = (
        await db.execute(
            select(func.count(InventoryItem.id)).where(
                (InventoryItem.quantity - InventoryItem.reserved) <= InventoryItem.low_stock_threshold
            )
        )
    ).scalar() or 0

    total_suppliers = (await db.execute(select(func.count(Supplier.id)))).scalar() or 0

    return DashboardStats(
        total_products=total_products,
        active_products=active_products,
        total_orders=total_orders,
        pending_orders=pending_orders,
        total_revenue=total_revenue,
        low_stock_count=low_stock,
        total_suppliers=total_suppliers,
    )
