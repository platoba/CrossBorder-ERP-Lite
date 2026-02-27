"""ERP data models."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Product(Base):
    """Central product catalog."""
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    category = Column(String(200), default="")
    brand = Column(String(200), default="")
    weight_g = Column(Integer, default=0)
    cost_price = Column(Numeric(10, 2), default=0)
    retail_price = Column(Numeric(10, 2), default=0)
    image_url = Column(String(1000), default="")
    active = Column(Boolean, default=True)
    custom_fields = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    platform_listings = relationship("PlatformListing", back_populates="product")
    inventory_items = relationship("InventoryItem", back_populates="product")


class PlatformListing(Base):
    """Product listing on a specific platform."""
    __tablename__ = "platform_listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    platform = Column(
        Enum("amazon", "shopify", "ebay", "aliexpress", "tiktok", "walmart", name="platform_type"),
        nullable=False,
    )
    platform_sku = Column(String(200), default="")
    platform_url = Column(String(1000), default="")
    listing_price = Column(Numeric(10, 2), default=0)
    currency = Column(String(3), default="USD")
    status = Column(Enum("active", "inactive", "draft", "suppressed", name="listing_status"), default="active")
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    product = relationship("Product", back_populates="platform_listings")


class InventoryItem(Base):
    """Inventory tracking per product per warehouse."""
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    warehouse = Column(String(100), default="default")
    quantity = Column(Integer, default=0)
    reserved = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=10)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product = relationship("Product", back_populates="inventory_items")

    @property
    def available(self) -> int:
        return max(0, self.quantity - self.reserved)

    @property
    def is_low_stock(self) -> bool:
        return self.available <= self.low_stock_threshold


class Order(Base):
    """Unified order from any platform."""
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(100), unique=True, nullable=False, index=True)
    platform = Column(
        Enum("amazon", "shopify", "ebay", "aliexpress", "tiktok", "walmart", "manual", name="order_platform"),
        nullable=False,
    )
    platform_order_id = Column(String(200), default="")
    status = Column(
        Enum("pending", "processing", "shipped", "delivered", "cancelled", "refunded", name="order_status"),
        default="pending",
    )
    customer_name = Column(String(300), default="")
    customer_email = Column(String(320), default="")
    shipping_address = Column(JSON, default=dict)
    subtotal = Column(Numeric(10, 2), default=0)
    shipping_cost = Column(Numeric(10, 2), default=0)
    tax = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), default=0)
    currency = Column(String(3), default="USD")
    tracking_number = Column(String(200), default="")
    shipping_carrier = Column(String(100), default="")
    notes = Column(Text, default="")
    ordered_at = Column(DateTime(timezone=True), nullable=True)
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    sku = Column(String(100), default="")
    title = Column(String(500), default="")
    quantity = Column(Integer, default=1)
    unit_price = Column(Numeric(10, 2), default=0)
    total_price = Column(Numeric(10, 2), default=0)

    order = relationship("Order", back_populates="items")


class Supplier(Base):
    """Supplier (1688, Alibaba, etc.)."""
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False)
    platform = Column(String(100), default="")  # 1688, alibaba, direct
    contact_name = Column(String(200), default="")
    contact_phone = Column(String(50), default="")
    contact_wechat = Column(String(100), default="")
    url = Column(String(1000), default="")
    rating = Column(Integer, default=0)  # 1-5
    lead_time_days = Column(Integer, default=7)
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)


class PurchaseOrder(Base):
    """Purchase order to supplier."""
    __tablename__ = "purchase_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_number = Column(String(100), unique=True, nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    status = Column(
        Enum("draft", "sent", "confirmed", "shipped", "received", "cancelled", name="po_status"),
        default="draft",
    )
    items = Column(JSON, default=list)  # [{sku, quantity, unit_cost}]
    total_cost = Column(Numeric(10, 2), default=0)
    currency = Column(String(3), default="CNY")
    expected_date = Column(DateTime(timezone=True), nullable=True)
    received_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
