"""Customer management models."""

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


class Customer(Base):
    """Unified customer record across all platforms."""
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), unique=True, nullable=False, index=True)
    name = Column(String(300), default="")
    phone = Column(String(50), default="")
    country = Column(String(2), default="")
    city = Column(String(200), default="")
    address = Column(Text, default="")
    tier = Column(
        Enum("regular", "vip", "wholesale", "blacklisted", name="customer_tier"),
        default="regular",
    )
    tags = Column(JSON, default=list)  # ["repeat_buyer", "high_value"]
    total_orders = Column(Integer, default=0)
    total_spent = Column(Numeric(12, 2), default=0)
    total_returns = Column(Integer, default=0)
    avg_order_value = Column(Numeric(10, 2), default=0)
    first_order_at = Column(DateTime(timezone=True), nullable=True)
    last_order_at = Column(DateTime(timezone=True), nullable=True)
    platform_ids = Column(JSON, default=dict)  # {"amazon": "...", "shopify": "..."}
    notes = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    interactions = relationship("CustomerInteraction", back_populates="customer")


class CustomerInteraction(Base):
    """Customer interaction / support ticket log."""
    __tablename__ = "customer_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    interaction_type = Column(
        Enum("inquiry", "complaint", "review", "return", "feedback", "support", name="interaction_type"),
        nullable=False,
    )
    channel = Column(String(50), default="email")  # email, chat, phone, platform
    subject = Column(String(500), default="")
    content = Column(Text, default="")
    sentiment = Column(
        Enum("positive", "neutral", "negative", name="sentiment_type"),
        default="neutral",
    )
    status = Column(
        Enum("open", "in_progress", "resolved", "closed", name="interaction_status"),
        default="open",
    )
    assigned_to = Column(String(200), default="")
    reference = Column(String(200), default="")  # order_number, return_number, etc.
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    customer = relationship("Customer", back_populates="interactions")
