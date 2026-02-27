"""Order CRUD API."""

import uuid as uuid_mod
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Order, OrderItem, Product
from app.schemas import OrderCreate, OrderOut, OrderUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


def _generate_order_number() -> str:
    return f"ORD-{uuid_mod.uuid4().hex[:8].upper()}"


@router.get("/", response_model=list[OrderOut])
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = None,
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    if platform:
        stmt = stmt.where(Order.platform == platform)
    stmt = stmt.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=OrderOut, status_code=201)
async def create_order(data: OrderCreate, db: AsyncSession = Depends(get_db)):
    subtotal = sum(i.unit_price * i.quantity for i in data.items)
    total = subtotal + data.shipping_cost + data.tax

    order = Order(
        order_number=_generate_order_number(),
        platform=data.platform,
        platform_order_id=data.platform_order_id,
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        shipping_address=data.shipping_address,
        subtotal=subtotal,
        shipping_cost=data.shipping_cost,
        tax=data.tax,
        total=total,
        currency=data.currency,
        notes=data.notes,
    )
    db.add(order)
    await db.flush()

    for item in data.items:
        # Try to find product by SKU
        result = await db.execute(select(Product).where(Product.sku == item.sku))
        product = result.scalar_one_or_none()

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id if product else None,
            sku=item.sku,
            title=item.title or (product.title if product else ""),
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.unit_price * item.quantity,
        )
        db.add(order_item)

    await db.commit()
    await db.refresh(order)
    return order


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    return order


@router.patch("/{order_id}", response_model=OrderOut)
async def update_order(order_id: UUID, data: OrderUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(order, key, val)
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/ship", response_model=OrderOut)
async def ship_order(
    order_id: UUID,
    tracking_number: str,
    carrier: str = "4PX",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status not in ("pending", "processing"):
        raise HTTPException(400, f"Cannot ship order in '{order.status}' status")

    from datetime import datetime, timezone
    order.status = "shipped"
    order.tracking_number = tracking_number
    order.shipping_carrier = carrier
    order.shipped_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(order)
    return order
