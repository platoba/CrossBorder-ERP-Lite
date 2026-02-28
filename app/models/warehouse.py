"""Warehouse management models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Warehouse(Base):
    """Physical warehouse / fulfillment center."""
    __tablename__ = "warehouses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(300), nullable=False)
    warehouse_type = Column(
        Enum("owned", "3pl", "fba", "overseas", "bonded", name="warehouse_type"),
        default="owned",
    )
    country = Column(String(2), default="CN")  # ISO 3166-1 alpha-2
    city = Column(String(200), default="")
    address = Column(Text, default="")
    contact_name = Column(String(200), default="")
    contact_phone = Column(String(50), default="")
    capacity_units = Column(Integer, default=0)  # max storage units
    is_active = Column(Boolean, default=True)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    transfers_out = relationship(
        "StockTransfer",
        back_populates="source_warehouse",
        foreign_keys="StockTransfer.source_warehouse_id",
    )
    transfers_in = relationship(
        "StockTransfer",
        back_populates="dest_warehouse",
        foreign_keys="StockTransfer.dest_warehouse_id",
    )


class StockTransfer(Base):
    """Stock transfer between warehouses."""
    __tablename__ = "stock_transfers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transfer_number = Column(String(100), unique=True, nullable=False, index=True)
    source_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    dest_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    status = Column(
        Enum("draft", "approved", "in_transit", "received", "cancelled", name="transfer_status"),
        default="draft",
    )
    items = Column(JSON, default=list)  # [{sku, quantity, product_id}]
    total_units = Column(Integer, default=0)
    shipping_carrier = Column(String(100), default="")
    tracking_number = Column(String(200), default="")
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    source_warehouse = relationship(
        "Warehouse", back_populates="transfers_out",
        foreign_keys=[source_warehouse_id],
    )
    dest_warehouse = relationship(
        "Warehouse", back_populates="transfers_in",
        foreign_keys=[dest_warehouse_id],
    )


class StockAdjustment(Base):
    """Manual stock adjustments (damage, returns, audits)."""
    __tablename__ = "stock_adjustments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    warehouse_code = Column(String(50), nullable=False)
    sku = Column(String(100), nullable=False)
    adjustment_type = Column(
        Enum("damage", "return", "audit", "correction", "write_off", name="adjustment_type"),
        nullable=False,
    )
    quantity_change = Column(Integer, nullable=False)  # positive = add, negative = remove
    reason = Column(Text, default="")
    reference = Column(String(200), default="")  # e.g. order number
    created_by = Column(String(200), default="system")
    created_at = Column(DateTime(timezone=True), default=utcnow)
