"""Warehouse management API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.warehouse import (
    AdjustmentRequest,
    TransferRequest,
    WarehouseInfo,
    WarehouseManager,
)

router = APIRouter(prefix="/warehouse", tags=["warehouse"])

# Singleton manager
_manager = WarehouseManager()


def get_manager() -> WarehouseManager:
    return _manager


# --- Schemas ---

class WarehouseCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=300)
    warehouse_type: str = "owned"
    country: str = "CN"
    city: str = ""
    address: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    capacity_units: int = 0


class TransferCreate(BaseModel):
    source_warehouse: str
    dest_warehouse: str
    items: list[dict]  # [{sku, quantity}]
    shipping_carrier: str = ""
    notes: str = ""


class TransferShip(BaseModel):
    tracking: str = ""
    carrier: str = ""


class AdjustmentCreate(BaseModel):
    warehouse_code: str
    sku: str
    adjustment_type: str
    quantity_change: int
    reason: str = ""
    reference: str = ""
    created_by: str = "system"


# --- Warehouse CRUD ---

@router.post("/warehouses", status_code=201)
async def create_warehouse(body: WarehouseCreate):
    mgr = get_manager()
    try:
        info = WarehouseInfo(
            code=body.code,
            name=body.name,
            warehouse_type=body.warehouse_type,
            country=body.country,
            city=body.city,
            address=body.address,
            contact_name=body.contact_name,
            contact_phone=body.contact_phone,
            capacity_units=body.capacity_units,
        )
        result = mgr.create_warehouse(info)
        return {"code": result.code, "name": result.name, "id": result.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/warehouses")
async def list_warehouses(
    active_only: bool = True,
    warehouse_type: Optional[str] = None,
    country: Optional[str] = None,
):
    mgr = get_manager()
    warehouses = mgr.list_warehouses(active_only, warehouse_type, country)
    return [
        {
            "code": w.code,
            "name": w.name,
            "warehouse_type": w.warehouse_type,
            "country": w.country,
            "city": w.city,
            "is_active": w.is_active,
            "capacity_units": w.capacity_units,
        }
        for w in warehouses
    ]


@router.get("/warehouses/{code}")
async def get_warehouse(code: str):
    mgr = get_manager()
    wh = mgr.get_warehouse(code)
    if not wh:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return {
        "code": wh.code,
        "name": wh.name,
        "warehouse_type": wh.warehouse_type,
        "country": wh.country,
        "city": wh.city,
        "is_active": wh.is_active,
        "stock": mgr.get_warehouse_stock(code),
    }


@router.delete("/warehouses/{code}")
async def deactivate_warehouse(code: str):
    mgr = get_manager()
    if not mgr.deactivate_warehouse(code):
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return {"status": "deactivated", "code": code}


# --- Stock ---

@router.put("/warehouses/{code}/stock/{sku}")
async def set_stock(code: str, sku: str, quantity: int):
    mgr = get_manager()
    if not mgr.get_warehouse(code):
        raise HTTPException(status_code=404, detail="Warehouse not found")
    mgr.set_stock(code, sku, quantity)
    return {"warehouse": code, "sku": sku, "quantity": quantity}


@router.get("/warehouses/{code}/stock")
async def get_warehouse_stock(code: str):
    mgr = get_manager()
    if not mgr.get_warehouse(code):
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return mgr.get_warehouse_stock(code)


@router.get("/stock/{sku}")
async def get_sku_stock(sku: str):
    mgr = get_manager()
    return mgr.get_total_stock(sku)


# --- Transfers ---

@router.post("/transfers", status_code=201)
async def create_transfer(body: TransferCreate):
    mgr = get_manager()
    try:
        req = TransferRequest(
            source_warehouse=body.source_warehouse,
            dest_warehouse=body.dest_warehouse,
            items=body.items,
            shipping_carrier=body.shipping_carrier,
            notes=body.notes,
        )
        return mgr.create_transfer(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfers/{number}/approve")
async def approve_transfer(number: str):
    mgr = get_manager()
    try:
        return mgr.approve_transfer(number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfers/{number}/ship")
async def ship_transfer(number: str, body: TransferShip):
    mgr = get_manager()
    try:
        return mgr.ship_transfer(number, body.tracking, body.carrier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfers/{number}/receive")
async def receive_transfer(number: str):
    mgr = get_manager()
    try:
        return mgr.receive_transfer(number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfers/{number}/cancel")
async def cancel_transfer(number: str):
    mgr = get_manager()
    try:
        return mgr.cancel_transfer(number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transfers")
async def list_transfers(
    status: Optional[str] = None,
    warehouse: Optional[str] = None,
):
    mgr = get_manager()
    return mgr.list_transfers(status, warehouse)


@router.get("/transfers/{number}")
async def get_transfer(number: str):
    mgr = get_manager()
    t = mgr.get_transfer(number)
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return t


# --- Adjustments ---

@router.post("/adjustments", status_code=201)
async def create_adjustment(body: AdjustmentCreate):
    mgr = get_manager()
    try:
        req = AdjustmentRequest(
            warehouse_code=body.warehouse_code,
            sku=body.sku,
            adjustment_type=body.adjustment_type,
            quantity_change=body.quantity_change,
            reason=body.reason,
            reference=body.reference,
            created_by=body.created_by,
        )
        return mgr.create_adjustment(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/adjustments")
async def list_adjustments(
    warehouse_code: Optional[str] = None,
    sku: Optional[str] = None,
    adjustment_type: Optional[str] = None,
):
    mgr = get_manager()
    return mgr.list_adjustments(warehouse_code, sku, adjustment_type)


# --- Summary ---

@router.get("/summary")
async def inventory_summary():
    mgr = get_manager()
    return mgr.inventory_summary()


@router.get("/alerts/low-stock")
async def low_stock_alerts(threshold: int = 10):
    mgr = get_manager()
    return mgr.low_stock_alerts(threshold)
