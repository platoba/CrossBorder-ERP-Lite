"""Inventory API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import InventoryItem
from app.schemas import InventoryOut, InventoryUpdate

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/", response_model=list[InventoryOut])
async def list_inventory(
    warehouse: str | None = None,
    low_stock: bool = False,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InventoryItem)
    if warehouse:
        stmt = stmt.where(InventoryItem.warehouse == warehouse)
    if low_stock:
        stmt = stmt.where(
            (InventoryItem.quantity - InventoryItem.reserved) <= InventoryItem.low_stock_threshold
        )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{item_id}", response_model=InventoryOut)
async def get_inventory_item(item_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Inventory item not found")
    return item


@router.patch("/{item_id}", response_model=InventoryOut)
async def update_inventory(item_id: UUID, data: InventoryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Inventory item not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(item, key, val)
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/{item_id}/adjust")
async def adjust_stock(
    item_id: UUID,
    delta: int = Query(..., description="Positive to add, negative to subtract"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(InventoryItem).where(InventoryItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Inventory item not found")
    new_qty = item.quantity + delta
    if new_qty < 0:
        raise HTTPException(400, "Stock cannot go below zero")
    item.quantity = new_qty
    await db.commit()
    return {"item_id": str(item_id), "new_quantity": new_qty}
