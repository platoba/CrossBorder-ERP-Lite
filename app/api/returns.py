"""Returns & refunds API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.returns import ReturnsManager, ReturnRequestData

router = APIRouter(prefix="/returns", tags=["returns"])

_manager = ReturnsManager(restocking_fee_pct=0.0)


def get_manager() -> ReturnsManager:
    return _manager


# --- Schemas ---

class ReturnCreate(BaseModel):
    order_number: str = Field(..., min_length=1)
    reason: str
    return_type: str = "refund"
    platform: str = ""
    customer_name: str = ""
    customer_email: str = ""
    items: list[dict] = Field(default_factory=list)
    customer_notes: str = ""
    images: list[str] = Field(default_factory=list)


class ReturnApprove(BaseModel):
    warehouse_code: str = ""
    internal_notes: str = ""


class ReturnReceive(BaseModel):
    qc_status: str = "passed"
    tracking: str = ""
    carrier: str = ""


class ReturnRefund(BaseModel):
    actual_refund: Optional[float] = None
    return_shipping_cost: float = 0.0


# --- Endpoints ---

@router.post("/", status_code=201)
async def create_return(body: ReturnCreate):
    mgr = get_manager()
    try:
        data = ReturnRequestData(
            order_number=body.order_number,
            reason=body.reason,
            return_type=body.return_type,
            platform=body.platform,
            customer_name=body.customer_name,
            customer_email=body.customer_email,
            items=body.items,
            customer_notes=body.customer_notes,
            images=body.images,
        )
        return mgr.create_return(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_returns(
    status: Optional[str] = None,
    order_number: Optional[str] = None,
    platform: Optional[str] = None,
    reason: Optional[str] = None,
):
    mgr = get_manager()
    return mgr.list_returns(status, order_number, platform, reason)


@router.get("/stats")
async def return_stats():
    mgr = get_manager()
    return mgr.stats()


@router.get("/{return_number}")
async def get_return(return_number: str):
    mgr = get_manager()
    ret = mgr.get_return(return_number)
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    return ret


@router.post("/{return_number}/approve")
async def approve_return(return_number: str, body: ReturnApprove):
    mgr = get_manager()
    try:
        return mgr.approve_return(return_number, body.warehouse_code, body.internal_notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_number}/reject")
async def reject_return(return_number: str, reason: str = ""):
    mgr = get_manager()
    try:
        return mgr.reject_return(return_number, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_number}/receive")
async def receive_item(return_number: str, body: ReturnReceive):
    mgr = get_manager()
    try:
        return mgr.receive_item(return_number, body.qc_status, body.tracking, body.carrier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_number}/refund")
async def process_refund(return_number: str, body: ReturnRefund):
    mgr = get_manager()
    try:
        return mgr.process_refund(return_number, body.actual_refund, body.return_shipping_cost)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{return_number}/close")
async def close_return(return_number: str):
    mgr = get_manager()
    try:
        return mgr.close_return(return_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
