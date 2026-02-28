"""Returns & refunds models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, JSON,
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class ReturnRequest(Base):
    """Customer return / refund request."""
    __tablename__ = "return_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_number = Column(String(100), unique=True, nullable=False, index=True)
    order_number = Column(String(100), nullable=False, index=True)
    platform = Column(String(50), default="")
    status = Column(
        Enum(
            "requested", "approved", "rejected",
            "item_received", "refunded", "closed",
            name="return_status",
        ),
        default="requested",
    )
    return_type = Column(
        Enum("refund", "replacement", "exchange", name="return_type"),
        default="refund",
    )
    reason = Column(
        Enum(
            "defective", "wrong_item", "not_as_described", "no_longer_needed",
            "arrived_late", "damaged_in_shipping", "other",
            name="return_reason",
        ),
        nullable=False,
    )
    customer_name = Column(String(300), default="")
    customer_email = Column(String(320), default="")
    items = Column(JSON, default=list)  # [{sku, quantity, unit_price}]
    refund_amount = Column(Numeric(10, 2), default=0)
    currency = Column(String(3), default="USD")
    restocking_fee = Column(Numeric(10, 2), default=0)
    return_shipping_cost = Column(Numeric(10, 2), default=0)
    return_tracking = Column(String(200), default="")
    return_carrier = Column(String(100), default="")
    warehouse_code = Column(String(50), default="")
    quality_check = Column(
        Enum("pending", "passed", "failed", "partial", name="qc_status"),
        default="pending",
    )
    customer_notes = Column(Text, default="")
    internal_notes = Column(Text, default="")
    images = Column(JSON, default=list)  # URLs of return item photos
    requested_at = Column(DateTime(timezone=True), default=utcnow)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
