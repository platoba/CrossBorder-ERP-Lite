"""Returns & refunds management service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


@dataclass
class ReturnItem:
    sku: str
    quantity: int
    unit_price: float = 0.0
    reason: str = ""


@dataclass
class ReturnRequestData:
    order_number: str
    reason: str
    return_type: str = "refund"  # refund, replacement, exchange
    platform: str = ""
    customer_name: str = ""
    customer_email: str = ""
    items: list[dict] = field(default_factory=list)
    customer_notes: str = ""
    images: list[str] = field(default_factory=list)


class ReturnsManager:
    """Returns and refunds management service."""

    VALID_REASONS = {
        "defective", "wrong_item", "not_as_described",
        "no_longer_needed", "arrived_late", "damaged_in_shipping", "other",
    }
    VALID_TYPES = {"refund", "replacement", "exchange"}
    VALID_STATUSES = {
        "requested", "approved", "rejected",
        "item_received", "refunded", "closed",
    }
    VALID_QC = {"pending", "passed", "failed", "partial"}

    def __init__(self, restocking_fee_pct: float = 0.0):
        self._returns: dict[str, dict] = {}
        self._counter = 0
        self._restocking_fee_pct = restocking_fee_pct

    def create_return(self, data: ReturnRequestData) -> dict:
        """Create a new return request."""
        if data.reason not in self.VALID_REASONS:
            raise ValueError(f"Invalid reason: {data.reason}")
        if data.return_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid return type: {data.return_type}")
        if not data.order_number:
            raise ValueError("Order number is required")
        if not data.items:
            raise ValueError("At least one item is required")

        self._counter += 1
        return_number = f"RET-{self._counter:06d}"

        subtotal = sum(
            item.get("unit_price", 0) * item.get("quantity", 0)
            for item in data.items
        )
        restocking_fee = round(subtotal * self._restocking_fee_pct, 2)
        refund_amount = round(subtotal - restocking_fee, 2)

        ret = {
            "id": str(uuid.uuid4()),
            "return_number": return_number,
            "order_number": data.order_number,
            "platform": data.platform,
            "status": "requested",
            "return_type": data.return_type,
            "reason": data.reason,
            "customer_name": data.customer_name,
            "customer_email": data.customer_email,
            "items": data.items,
            "refund_amount": refund_amount,
            "currency": "USD",
            "restocking_fee": restocking_fee,
            "return_shipping_cost": 0.0,
            "return_tracking": "",
            "return_carrier": "",
            "warehouse_code": "",
            "quality_check": "pending",
            "customer_notes": data.customer_notes,
            "internal_notes": "",
            "images": data.images,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "approved_at": None,
            "received_at": None,
            "refunded_at": None,
            "closed_at": None,
        }
        self._returns[return_number] = ret
        return ret

    def get_return(self, return_number: str) -> Optional[dict]:
        return self._returns.get(return_number)

    def approve_return(
        self,
        return_number: str,
        warehouse_code: str = "",
        internal_notes: str = "",
    ) -> dict:
        """Approve a return request."""
        ret = self._returns.get(return_number)
        if not ret:
            raise ValueError(f"Return not found: {return_number}")
        if ret["status"] != "requested":
            raise ValueError(f"Cannot approve return in status: {ret['status']}")
        ret["status"] = "approved"
        ret["warehouse_code"] = warehouse_code
        ret["internal_notes"] = internal_notes
        ret["approved_at"] = datetime.now(timezone.utc).isoformat()
        return ret

    def reject_return(self, return_number: str, reason: str = "") -> dict:
        """Reject a return request."""
        ret = self._returns.get(return_number)
        if not ret:
            raise ValueError(f"Return not found: {return_number}")
        if ret["status"] != "requested":
            raise ValueError(f"Cannot reject return in status: {ret['status']}")
        ret["status"] = "rejected"
        ret["internal_notes"] = reason
        ret["closed_at"] = datetime.now(timezone.utc).isoformat()
        return ret

    def receive_item(
        self,
        return_number: str,
        qc_status: str = "passed",
        tracking: str = "",
        carrier: str = "",
    ) -> dict:
        """Mark return item as received at warehouse."""
        ret = self._returns.get(return_number)
        if not ret:
            raise ValueError(f"Return not found: {return_number}")
        if ret["status"] != "approved":
            raise ValueError(f"Cannot receive item for return in status: {ret['status']}")
        if qc_status not in self.VALID_QC:
            raise ValueError(f"Invalid QC status: {qc_status}")
        ret["status"] = "item_received"
        ret["quality_check"] = qc_status
        ret["return_tracking"] = tracking
        ret["return_carrier"] = carrier
        ret["received_at"] = datetime.now(timezone.utc).isoformat()
        return ret

    def process_refund(
        self,
        return_number: str,
        actual_refund: Optional[float] = None,
        return_shipping_cost: float = 0.0,
    ) -> dict:
        """Process the refund for a return."""
        ret = self._returns.get(return_number)
        if not ret:
            raise ValueError(f"Return not found: {return_number}")
        if ret["status"] != "item_received":
            raise ValueError(f"Cannot refund return in status: {ret['status']}")
        if actual_refund is not None:
            ret["refund_amount"] = actual_refund
        ret["return_shipping_cost"] = return_shipping_cost
        ret["status"] = "refunded"
        ret["refunded_at"] = datetime.now(timezone.utc).isoformat()
        return ret

    def close_return(self, return_number: str) -> dict:
        """Close a return (after refund or rejection)."""
        ret = self._returns.get(return_number)
        if not ret:
            raise ValueError(f"Return not found: {return_number}")
        if ret["status"] not in ("refunded", "rejected"):
            raise ValueError(f"Cannot close return in status: {ret['status']}")
        ret["status"] = "closed"
        ret["closed_at"] = datetime.now(timezone.utc).isoformat()
        return ret

    def list_returns(
        self,
        status: Optional[str] = None,
        order_number: Optional[str] = None,
        platform: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> list[dict]:
        result = list(self._returns.values())
        if status:
            result = [r for r in result if r["status"] == status]
        if order_number:
            result = [r for r in result if r["order_number"] == order_number]
        if platform:
            result = [r for r in result if r["platform"] == platform]
        if reason:
            result = [r for r in result if r["reason"] == reason]
        return result

    def stats(self) -> dict:
        """Return statistics on returns."""
        total = len(self._returns)
        if total == 0:
            return {
                "total": 0,
                "by_status": {},
                "by_reason": {},
                "by_type": {},
                "total_refunded": 0.0,
                "avg_refund": 0.0,
            }

        by_status: dict[str, int] = {}
        by_reason: dict[str, int] = {}
        by_type: dict[str, int] = {}
        total_refunded = 0.0

        for ret in self._returns.values():
            by_status[ret["status"]] = by_status.get(ret["status"], 0) + 1
            by_reason[ret["reason"]] = by_reason.get(ret["reason"], 0) + 1
            by_type[ret["return_type"]] = by_type.get(ret["return_type"], 0) + 1
            if ret["status"] in ("refunded", "closed"):
                total_refunded += ret["refund_amount"]

        return {
            "total": total,
            "by_status": by_status,
            "by_reason": by_reason,
            "by_type": by_type,
            "total_refunded": round(total_refunded, 2),
            "avg_refund": round(total_refunded / max(1, by_status.get("refunded", 0) + by_status.get("closed", 0)), 2),
        }

    def return_rate(self, total_orders: int) -> float:
        """Calculate return rate as percentage."""
        if total_orders <= 0:
            return 0.0
        return round(len(self._returns) / total_orders * 100, 2)
