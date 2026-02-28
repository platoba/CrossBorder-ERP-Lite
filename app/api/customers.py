"""Customer management API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.services.customer import CustomerData, CustomerManager, InteractionData

router = APIRouter(prefix="/customers", tags=["customers"])

_manager = CustomerManager()


def get_manager() -> CustomerManager:
    return _manager


# --- Schemas ---

class CustomerCreate(BaseModel):
    email: EmailStr
    name: str = ""
    phone: str = ""
    country: str = ""
    city: str = ""
    address: str = ""
    tier: str = "regular"
    tags: list[str] = Field(default_factory=list)
    platform_ids: dict[str, str] = Field(default_factory=dict)
    notes: str = ""


class TierUpdate(BaseModel):
    tier: str


class TagsAdd(BaseModel):
    tags: list[str]


class OrderRecord(BaseModel):
    order_total: float


class InteractionCreate(BaseModel):
    interaction_type: str
    channel: str = "email"
    subject: str = ""
    content: str = ""
    sentiment: str = "neutral"
    assigned_to: str = ""
    reference: str = ""


class InteractionStatusUpdate(BaseModel):
    status: str


# --- Customer CRUD ---

@router.post("/", status_code=201)
async def create_customer(body: CustomerCreate):
    mgr = get_manager()
    try:
        data = CustomerData(
            email=body.email,
            name=body.name,
            phone=body.phone,
            country=body.country,
            city=body.city,
            address=body.address,
            tier=body.tier,
            tags=body.tags,
            platform_ids=body.platform_ids,
            notes=body.notes,
        )
        return mgr.create_customer(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_customers(
    tier: Optional[str] = None,
    country: Optional[str] = None,
    active_only: bool = True,
    tag: Optional[str] = None,
    min_orders: int = 0,
    sort_by: str = "total_spent",
    limit: int = 100,
):
    mgr = get_manager()
    return mgr.list_customers(tier, country, active_only, tag, min_orders, sort_by, limit)


@router.get("/search")
async def search_customers(q: str):
    mgr = get_manager()
    return mgr.search_customers(q)


@router.get("/stats")
async def customer_stats():
    mgr = get_manager()
    return mgr.stats()


@router.get("/{email}")
async def get_customer(email: str):
    mgr = get_manager()
    c = mgr.get_customer(email)
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")
    return c


@router.delete("/{email}")
async def deactivate_customer(email: str):
    mgr = get_manager()
    if not mgr.deactivate_customer(email):
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"status": "deactivated", "email": email}


@router.put("/{email}/tier")
async def update_tier(email: str, body: TierUpdate):
    mgr = get_manager()
    try:
        return mgr.set_tier(email, body.tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{email}/tags")
async def add_tags(email: str, body: TagsAdd):
    mgr = get_manager()
    try:
        return mgr.add_tags(email, body.tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{email}/order")
async def record_order(email: str, body: OrderRecord):
    mgr = get_manager()
    try:
        return mgr.record_order(email, body.order_total)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{email}/return")
async def record_return(email: str):
    mgr = get_manager()
    try:
        return mgr.record_return(email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{email}/health")
async def health_score(email: str):
    mgr = get_manager()
    try:
        return mgr.customer_health_score(email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Interactions ---

@router.post("/{email}/interactions", status_code=201)
async def create_interaction(email: str, body: InteractionCreate):
    mgr = get_manager()
    try:
        data = InteractionData(
            customer_email=email,
            interaction_type=body.interaction_type,
            channel=body.channel,
            subject=body.subject,
            content=body.content,
            sentiment=body.sentiment,
            assigned_to=body.assigned_to,
            reference=body.reference,
        )
        return mgr.create_interaction(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{email}/interactions")
async def list_interactions(
    email: str,
    interaction_type: Optional[str] = None,
    status: Optional[str] = None,
    sentiment: Optional[str] = None,
):
    mgr = get_manager()
    return mgr.list_interactions(email, interaction_type, status, sentiment)


@router.put("/interactions/{interaction_id}/status")
async def update_interaction_status(interaction_id: str, body: InteractionStatusUpdate):
    mgr = get_manager()
    try:
        return mgr.update_interaction_status(interaction_id, body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
