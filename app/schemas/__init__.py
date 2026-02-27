"""Pydantic schemas for ERP API."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Product ──────────────────────────────────────────────
class ProductCreate(BaseModel):
    sku: str
    title: str
    description: str = ""
    category: str = ""
    brand: str = ""
    weight_g: int = 0
    cost_price: Decimal = Decimal("0")
    retail_price: Decimal = Decimal("0")
    image_url: str = ""


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    cost_price: Optional[Decimal] = None
    retail_price: Optional[Decimal] = None
    active: Optional[bool] = None


class ProductOut(BaseModel):
    id: UUID
    sku: str
    title: str
    description: str
    category: str
    brand: str
    weight_g: int
    cost_price: Decimal
    retail_price: Decimal
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Order ────────────────────────────────────────────────
class OrderItemCreate(BaseModel):
    sku: str
    title: str = ""
    quantity: int = 1
    unit_price: Decimal = Decimal("0")


class OrderCreate(BaseModel):
    platform: str
    platform_order_id: str = ""
    customer_name: str = ""
    customer_email: str = ""
    shipping_address: dict = Field(default_factory=dict)
    items: list[OrderItemCreate] = Field(default_factory=list)
    shipping_cost: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    currency: str = "USD"
    notes: str = ""


class OrderUpdate(BaseModel):
    status: Optional[str] = None
    tracking_number: Optional[str] = None
    shipping_carrier: Optional[str] = None
    notes: Optional[str] = None


class OrderOut(BaseModel):
    id: UUID
    order_number: str
    platform: str
    status: str
    customer_name: str
    subtotal: Decimal
    shipping_cost: Decimal
    total: Decimal
    currency: str
    tracking_number: str
    ordered_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Inventory ────────────────────────────────────────────
class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    reserved: Optional[int] = None
    low_stock_threshold: Optional[int] = None


class InventoryOut(BaseModel):
    id: UUID
    product_id: UUID
    warehouse: str
    quantity: int
    reserved: int
    low_stock_threshold: int
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Supplier ─────────────────────────────────────────────
class SupplierCreate(BaseModel):
    name: str
    platform: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    contact_wechat: str = ""
    url: str = ""
    rating: int = 0
    lead_time_days: int = 7
    notes: str = ""


class SupplierOut(SupplierCreate):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard ────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_products: int
    active_products: int
    total_orders: int
    pending_orders: int
    total_revenue: Decimal
    low_stock_count: int
    total_suppliers: int
