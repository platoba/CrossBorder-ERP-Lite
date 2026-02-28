"""Purchase Order management API."""

import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import PurchaseOrder, Supplier

router = APIRouter(prefix="/purchase-orders", tags=["purchase_orders"])


class POItemSchema(BaseModel):
    sku: str
    quantity: int = 1
    unit_cost: float = 0.0


class POCreate(BaseModel):
    supplier_id: UUID
    items: list[POItemSchema] = Field(default_factory=list)
    currency: str = "CNY"
    expected_date: str | None = None
    notes: str = ""


class POUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    expected_date: str | None = None


class POOut(BaseModel):
    id: UUID
    po_number: str
    supplier_id: UUID
    status: str
    items: list
    total_cost: float
    currency: str
    notes: str
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, po: PurchaseOrder) -> "POOut":
        return cls(
            id=po.id,
            po_number=po.po_number,
            supplier_id=po.supplier_id,
            status=po.status.value if hasattr(po.status, "value") else str(po.status),
            items=po.items or [],
            total_cost=float(po.total_cost or 0),
            currency=po.currency or "CNY",
            notes=po.notes or "",
            created_at=po.created_at.isoformat() if po.created_at else "",
        )


def _generate_po_number() -> str:
    return f"PO-{uuid_mod.uuid4().hex[:8].upper()}"


@router.get("/")
async def list_purchase_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PurchaseOrder)
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)
    stmt = stmt.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    pos = result.scalars().all()
    return [POOut.from_orm_model(po) for po in pos]


@router.post("/", status_code=201)
async def create_purchase_order(data: POCreate, db: AsyncSession = Depends(get_db)):
    # Verify supplier exists
    result = await db.execute(select(Supplier).where(Supplier.id == data.supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(404, "Supplier not found")

    items_list = [item.model_dump() for item in data.items]
    total = sum(i["quantity"] * i["unit_cost"] for i in items_list)

    po = PurchaseOrder(
        po_number=_generate_po_number(),
        supplier_id=data.supplier_id,
        items=items_list,
        total_cost=total,
        currency=data.currency,
        notes=data.notes,
    )
    db.add(po)
    await db.commit()
    await db.refresh(po)
    return POOut.from_orm_model(po)


@router.get("/{po_id}")
async def get_purchase_order(po_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, "Purchase order not found")
    return POOut.from_orm_model(po)


@router.patch("/{po_id}")
async def update_purchase_order(
    po_id: UUID,
    data: POUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, "Purchase order not found")

    if data.status:
        po.status = data.status
    if data.notes is not None:
        po.notes = data.notes
    await db.commit()
    await db.refresh(po)
    return POOut.from_orm_model(po)


@router.post("/{po_id}/receive")
async def receive_purchase_order(
    po_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Mark a PO as received."""
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, "Purchase order not found")
    if po.status not in ("draft", "sent", "confirmed", "shipped"):
        raise HTTPException(400, f"Cannot receive PO in '{po.status}' status")

    from datetime import datetime, timezone
    po.status = "received"
    po.received_date = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(po)
    return POOut.from_orm_model(po)


@router.delete("/{po_id}", status_code=204)
async def delete_purchase_order(po_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, "Purchase order not found")
    if po.status not in ("draft", "cancelled"):
        raise HTTPException(400, "Can only delete draft or cancelled POs")
    await db.delete(po)
    await db.commit()
