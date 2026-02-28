"""Customer management service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


@dataclass
class CustomerData:
    email: str
    name: str = ""
    phone: str = ""
    country: str = ""
    city: str = ""
    address: str = ""
    tier: str = "regular"
    tags: list[str] = field(default_factory=list)
    platform_ids: dict[str, str] = field(default_factory=dict)
    notes: str = ""


@dataclass
class InteractionData:
    customer_email: str
    interaction_type: str  # inquiry, complaint, review, return, feedback, support
    channel: str = "email"
    subject: str = ""
    content: str = ""
    sentiment: str = "neutral"
    assigned_to: str = ""
    reference: str = ""


class CustomerManager:
    """In-memory customer management service."""

    VALID_TIERS = {"regular", "vip", "wholesale", "blacklisted"}
    VALID_INTERACTION_TYPES = {"inquiry", "complaint", "review", "return", "feedback", "support"}
    VALID_SENTIMENTS = {"positive", "neutral", "negative"}
    VALID_INTERACTION_STATUS = {"open", "in_progress", "resolved", "closed"}

    def __init__(self):
        self._customers: dict[str, dict] = {}  # email -> customer
        self._interactions: list[dict] = []

    def create_customer(self, data: CustomerData) -> dict:
        """Create or update a customer."""
        if not data.email:
            raise ValueError("Email is required")
        if data.tier not in self.VALID_TIERS:
            raise ValueError(f"Invalid tier: {data.tier}")

        existing = self._customers.get(data.email)
        now = datetime.now(timezone.utc).isoformat()

        if existing:
            # Update existing
            existing["name"] = data.name or existing["name"]
            existing["phone"] = data.phone or existing["phone"]
            existing["country"] = data.country or existing["country"]
            existing["city"] = data.city or existing["city"]
            existing["address"] = data.address or existing["address"]
            existing["tier"] = data.tier
            existing["tags"] = list(set(existing["tags"] + data.tags))
            existing["platform_ids"].update(data.platform_ids)
            existing["notes"] = data.notes or existing["notes"]
            existing["updated_at"] = now
            return existing

        customer = {
            "id": str(uuid.uuid4()),
            "email": data.email,
            "name": data.name,
            "phone": data.phone,
            "country": data.country,
            "city": data.city,
            "address": data.address,
            "tier": data.tier,
            "tags": data.tags,
            "total_orders": 0,
            "total_spent": 0.0,
            "total_returns": 0,
            "avg_order_value": 0.0,
            "first_order_at": None,
            "last_order_at": None,
            "platform_ids": data.platform_ids,
            "notes": data.notes,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        self._customers[data.email] = customer
        return customer

    def get_customer(self, email: str) -> Optional[dict]:
        return self._customers.get(email)

    def get_customer_by_id(self, customer_id: str) -> Optional[dict]:
        for c in self._customers.values():
            if c["id"] == customer_id:
                return c
        return None

    def deactivate_customer(self, email: str) -> bool:
        c = self._customers.get(email)
        if not c:
            return False
        c["is_active"] = False
        return True

    def set_tier(self, email: str, tier: str) -> dict:
        if tier not in self.VALID_TIERS:
            raise ValueError(f"Invalid tier: {tier}")
        c = self._customers.get(email)
        if not c:
            raise ValueError(f"Customer not found: {email}")
        c["tier"] = tier
        c["updated_at"] = datetime.now(timezone.utc).isoformat()
        return c

    def add_tags(self, email: str, tags: list[str]) -> dict:
        c = self._customers.get(email)
        if not c:
            raise ValueError(f"Customer not found: {email}")
        c["tags"] = list(set(c["tags"] + tags))
        c["updated_at"] = datetime.now(timezone.utc).isoformat()
        return c

    def record_order(self, email: str, order_total: float) -> dict:
        """Record a new order for a customer (updates stats)."""
        c = self._customers.get(email)
        if not c:
            raise ValueError(f"Customer not found: {email}")
        now = datetime.now(timezone.utc).isoformat()
        c["total_orders"] += 1
        c["total_spent"] = round(c["total_spent"] + order_total, 2)
        c["avg_order_value"] = round(c["total_spent"] / c["total_orders"], 2)
        if not c["first_order_at"]:
            c["first_order_at"] = now
        c["last_order_at"] = now
        c["updated_at"] = now

        # Auto-tier upgrade
        if c["total_orders"] >= 10 or c["total_spent"] >= 1000:
            if c["tier"] == "regular":
                c["tier"] = "vip"
                if "auto_upgraded" not in c["tags"]:
                    c["tags"].append("auto_upgraded")

        return c

    def record_return(self, email: str) -> dict:
        """Record a return for a customer."""
        c = self._customers.get(email)
        if not c:
            raise ValueError(f"Customer not found: {email}")
        c["total_returns"] += 1
        c["updated_at"] = datetime.now(timezone.utc).isoformat()
        return c

    def list_customers(
        self,
        tier: Optional[str] = None,
        country: Optional[str] = None,
        active_only: bool = True,
        tag: Optional[str] = None,
        min_orders: int = 0,
        sort_by: str = "total_spent",
        limit: int = 100,
    ) -> list[dict]:
        result = list(self._customers.values())
        if active_only:
            result = [c for c in result if c["is_active"]]
        if tier:
            result = [c for c in result if c["tier"] == tier]
        if country:
            result = [c for c in result if c["country"] == country]
        if tag:
            result = [c for c in result if tag in c["tags"]]
        if min_orders > 0:
            result = [c for c in result if c["total_orders"] >= min_orders]
        if sort_by in ("total_spent", "total_orders", "avg_order_value"):
            result.sort(key=lambda c: c.get(sort_by, 0), reverse=True)
        return result[:limit]

    def search_customers(self, query: str) -> list[dict]:
        """Search by name or email."""
        q = query.lower()
        return [
            c for c in self._customers.values()
            if q in c["email"].lower() or q in c["name"].lower()
        ]

    def create_interaction(self, data: InteractionData) -> dict:
        """Log a customer interaction."""
        if data.interaction_type not in self.VALID_INTERACTION_TYPES:
            raise ValueError(f"Invalid type: {data.interaction_type}")
        if data.sentiment not in self.VALID_SENTIMENTS:
            raise ValueError(f"Invalid sentiment: {data.sentiment}")
        c = self._customers.get(data.customer_email)
        if not c:
            raise ValueError(f"Customer not found: {data.customer_email}")

        interaction = {
            "id": str(uuid.uuid4()),
            "customer_id": c["id"],
            "customer_email": data.customer_email,
            "interaction_type": data.interaction_type,
            "channel": data.channel,
            "subject": data.subject,
            "content": data.content,
            "sentiment": data.sentiment,
            "status": "open",
            "assigned_to": data.assigned_to,
            "reference": data.reference,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._interactions.append(interaction)
        return interaction

    def update_interaction_status(self, interaction_id: str, status: str) -> dict:
        if status not in self.VALID_INTERACTION_STATUS:
            raise ValueError(f"Invalid status: {status}")
        for i in self._interactions:
            if i["id"] == interaction_id:
                i["status"] = status
                i["updated_at"] = datetime.now(timezone.utc).isoformat()
                return i
        raise ValueError(f"Interaction not found: {interaction_id}")

    def list_interactions(
        self,
        customer_email: Optional[str] = None,
        interaction_type: Optional[str] = None,
        status: Optional[str] = None,
        sentiment: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        result = list(self._interactions)
        if customer_email:
            result = [i for i in result if i["customer_email"] == customer_email]
        if interaction_type:
            result = [i for i in result if i["interaction_type"] == interaction_type]
        if status:
            result = [i for i in result if i["status"] == status]
        if sentiment:
            result = [i for i in result if i["sentiment"] == sentiment]
        return result[:limit]

    def customer_health_score(self, email: str) -> dict:
        """Calculate a customer health score (0-100)."""
        c = self._customers.get(email)
        if not c:
            raise ValueError(f"Customer not found: {email}")

        score = 50  # base

        # Orders boost
        score += min(20, c["total_orders"] * 2)

        # Spending boost
        if c["total_spent"] >= 500:
            score += 10
        elif c["total_spent"] >= 100:
            score += 5

        # Returns penalty
        if c["total_orders"] > 0:
            return_rate = c["total_returns"] / c["total_orders"]
            if return_rate > 0.3:
                score -= 20
            elif return_rate > 0.1:
                score -= 10

        # Interactions sentiment
        interactions = self.list_interactions(customer_email=email)
        neg_count = sum(1 for i in interactions if i["sentiment"] == "negative")
        pos_count = sum(1 for i in interactions if i["sentiment"] == "positive")
        score += min(10, pos_count * 2)
        score -= min(15, neg_count * 3)

        # Tier bonus
        if c["tier"] == "vip":
            score += 5
        elif c["tier"] == "wholesale":
            score += 3
        elif c["tier"] == "blacklisted":
            score -= 30

        score = max(0, min(100, score))

        return {
            "email": email,
            "name": c["name"],
            "score": score,
            "tier": c["tier"],
            "total_orders": c["total_orders"],
            "total_spent": c["total_spent"],
            "total_returns": c["total_returns"],
            "label": "excellent" if score >= 80 else "good" if score >= 60 else "fair" if score >= 40 else "at_risk",
        }

    def stats(self) -> dict:
        """Customer statistics."""
        total = len(self._customers)
        if total == 0:
            return {"total": 0, "active": 0, "by_tier": {}, "total_revenue": 0.0, "avg_ltv": 0.0}

        active = sum(1 for c in self._customers.values() if c["is_active"])
        by_tier: dict[str, int] = {}
        total_revenue = 0.0
        for c in self._customers.values():
            by_tier[c["tier"]] = by_tier.get(c["tier"], 0) + 1
            total_revenue += c["total_spent"]

        return {
            "total": total,
            "active": active,
            "by_tier": by_tier,
            "total_revenue": round(total_revenue, 2),
            "avg_ltv": round(total_revenue / total, 2),
            "total_interactions": len(self._interactions),
        }
