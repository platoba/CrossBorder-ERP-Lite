"""Warehouse management service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class WarehouseInfo:
    """Warehouse data structure."""
    code: str
    name: str
    warehouse_type: str = "owned"
    country: str = "CN"
    city: str = ""
    address: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    capacity_units: int = 0
    is_active: bool = True
    meta: dict = field(default_factory=dict)
    id: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class TransferRequest:
    """Stock transfer between warehouses."""
    source_warehouse: str  # warehouse code
    dest_warehouse: str
    items: list  # [{sku, quantity}]
    shipping_carrier: str = ""
    notes: str = ""


@dataclass
class AdjustmentRequest:
    """Manual stock adjustment."""
    warehouse_code: str
    sku: str
    adjustment_type: str  # damage, return, audit, correction, write_off
    quantity_change: int
    reason: str = ""
    reference: str = ""
    created_by: str = "system"


class WarehouseManager:
    """In-memory warehouse management for the ERP."""

    VALID_TYPES = {"owned", "3pl", "fba", "overseas", "bonded"}
    VALID_ADJUSTMENTS = {"damage", "return", "audit", "correction", "write_off"}
    VALID_TRANSFER_STATUS = {"draft", "approved", "in_transit", "received", "cancelled"}

    def __init__(self):
        self._warehouses: dict[str, WarehouseInfo] = {}
        self._transfers: dict[str, dict] = {}
        self._adjustments: list[dict] = []
        self._inventory: dict[str, dict[str, int]] = {}  # {warehouse_code: {sku: qty}}
        self._transfer_counter = 0

    def create_warehouse(self, info: WarehouseInfo) -> WarehouseInfo:
        """Create or update a warehouse."""
        if info.warehouse_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid warehouse type: {info.warehouse_type}")
        if not info.code or not info.name:
            raise ValueError("Warehouse code and name are required")
        info.id = info.id or str(uuid.uuid4())
        info.created_at = info.created_at or datetime.now(timezone.utc).isoformat()
        self._warehouses[info.code] = info
        if info.code not in self._inventory:
            self._inventory[info.code] = {}
        return info

    def get_warehouse(self, code: str) -> Optional[WarehouseInfo]:
        return self._warehouses.get(code)

    def list_warehouses(
        self,
        active_only: bool = True,
        warehouse_type: Optional[str] = None,
        country: Optional[str] = None,
    ) -> list[WarehouseInfo]:
        """List warehouses with optional filters."""
        result = list(self._warehouses.values())
        if active_only:
            result = [w for w in result if w.is_active]
        if warehouse_type:
            result = [w for w in result if w.warehouse_type == warehouse_type]
        if country:
            result = [w for w in result if w.country == country]
        return result

    def deactivate_warehouse(self, code: str) -> bool:
        wh = self._warehouses.get(code)
        if not wh:
            return False
        wh.is_active = False
        return True

    def set_stock(self, warehouse_code: str, sku: str, quantity: int) -> None:
        """Set absolute stock level."""
        if warehouse_code not in self._inventory:
            self._inventory[warehouse_code] = {}
        self._inventory[warehouse_code][sku] = max(0, quantity)

    def get_stock(self, warehouse_code: str, sku: str) -> int:
        return self._inventory.get(warehouse_code, {}).get(sku, 0)

    def get_warehouse_stock(self, warehouse_code: str) -> dict[str, int]:
        """Get all stock in a warehouse."""
        return dict(self._inventory.get(warehouse_code, {}))

    def get_total_stock(self, sku: str) -> dict[str, int]:
        """Get stock across all warehouses for a SKU."""
        result = {}
        for wh_code, stock in self._inventory.items():
            if sku in stock:
                result[wh_code] = stock[sku]
        return result

    def create_transfer(self, req: TransferRequest) -> dict:
        """Create a stock transfer between warehouses."""
        if req.source_warehouse == req.dest_warehouse:
            raise ValueError("Source and destination warehouse must be different")
        if req.source_warehouse not in self._warehouses:
            raise ValueError(f"Source warehouse not found: {req.source_warehouse}")
        if req.dest_warehouse not in self._warehouses:
            raise ValueError(f"Destination warehouse not found: {req.dest_warehouse}")
        if not req.items:
            raise ValueError("Transfer must have at least one item")

        # Validate stock availability
        for item in req.items:
            available = self.get_stock(req.source_warehouse, item["sku"])
            if available < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for {item['sku']}: "
                    f"available={available}, requested={item['quantity']}"
                )

        self._transfer_counter += 1
        transfer_number = f"TRF-{self._transfer_counter:06d}"
        total_units = sum(i["quantity"] for i in req.items)

        transfer = {
            "id": str(uuid.uuid4()),
            "transfer_number": transfer_number,
            "source_warehouse": req.source_warehouse,
            "dest_warehouse": req.dest_warehouse,
            "status": "draft",
            "items": req.items,
            "total_units": total_units,
            "shipping_carrier": req.shipping_carrier,
            "tracking_number": "",
            "notes": req.notes,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._transfers[transfer_number] = transfer
        return transfer

    def approve_transfer(self, transfer_number: str) -> dict:
        """Approve and deduct source stock."""
        transfer = self._transfers.get(transfer_number)
        if not transfer:
            raise ValueError(f"Transfer not found: {transfer_number}")
        if transfer["status"] != "draft":
            raise ValueError(f"Cannot approve transfer in status: {transfer['status']}")

        # Deduct from source
        for item in transfer["items"]:
            current = self.get_stock(transfer["source_warehouse"], item["sku"])
            self.set_stock(transfer["source_warehouse"], item["sku"], current - item["quantity"])

        transfer["status"] = "approved"
        return transfer

    def ship_transfer(self, transfer_number: str, tracking: str = "", carrier: str = "") -> dict:
        transfer = self._transfers.get(transfer_number)
        if not transfer:
            raise ValueError(f"Transfer not found: {transfer_number}")
        if transfer["status"] != "approved":
            raise ValueError(f"Cannot ship transfer in status: {transfer['status']}")
        transfer["status"] = "in_transit"
        transfer["tracking_number"] = tracking
        transfer["shipping_carrier"] = carrier
        transfer["shipped_at"] = datetime.now(timezone.utc).isoformat()
        return transfer

    def receive_transfer(self, transfer_number: str) -> dict:
        """Mark transfer as received and add stock to destination."""
        transfer = self._transfers.get(transfer_number)
        if not transfer:
            raise ValueError(f"Transfer not found: {transfer_number}")
        if transfer["status"] not in ("approved", "in_transit"):
            raise ValueError(f"Cannot receive transfer in status: {transfer['status']}")

        # Add to destination
        for item in transfer["items"]:
            current = self.get_stock(transfer["dest_warehouse"], item["sku"])
            self.set_stock(transfer["dest_warehouse"], item["sku"], current + item["quantity"])

        transfer["status"] = "received"
        transfer["received_at"] = datetime.now(timezone.utc).isoformat()
        return transfer

    def cancel_transfer(self, transfer_number: str) -> dict:
        """Cancel a transfer and restore stock if approved."""
        transfer = self._transfers.get(transfer_number)
        if not transfer:
            raise ValueError(f"Transfer not found: {transfer_number}")
        if transfer["status"] == "received":
            raise ValueError("Cannot cancel a received transfer")

        # Restore source stock if already deducted
        if transfer["status"] in ("approved", "in_transit"):
            for item in transfer["items"]:
                current = self.get_stock(transfer["source_warehouse"], item["sku"])
                self.set_stock(
                    transfer["source_warehouse"], item["sku"],
                    current + item["quantity"],
                )

        transfer["status"] = "cancelled"
        return transfer

    def get_transfer(self, transfer_number: str) -> Optional[dict]:
        return self._transfers.get(transfer_number)

    def list_transfers(
        self,
        status: Optional[str] = None,
        warehouse_code: Optional[str] = None,
    ) -> list[dict]:
        result = list(self._transfers.values())
        if status:
            result = [t for t in result if t["status"] == status]
        if warehouse_code:
            result = [
                t for t in result
                if t["source_warehouse"] == warehouse_code
                or t["dest_warehouse"] == warehouse_code
            ]
        return result

    def create_adjustment(self, req: AdjustmentRequest) -> dict:
        """Create a stock adjustment."""
        if req.adjustment_type not in self.VALID_ADJUSTMENTS:
            raise ValueError(f"Invalid adjustment type: {req.adjustment_type}")
        if req.quantity_change == 0:
            raise ValueError("Quantity change cannot be zero")

        current = self.get_stock(req.warehouse_code, req.sku)
        new_qty = max(0, current + req.quantity_change)
        self.set_stock(req.warehouse_code, req.sku, new_qty)

        adj = {
            "id": str(uuid.uuid4()),
            "warehouse_code": req.warehouse_code,
            "sku": req.sku,
            "adjustment_type": req.adjustment_type,
            "quantity_change": req.quantity_change,
            "previous_quantity": current,
            "new_quantity": new_qty,
            "reason": req.reason,
            "reference": req.reference,
            "created_by": req.created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._adjustments.append(adj)
        return adj

    def list_adjustments(
        self,
        warehouse_code: Optional[str] = None,
        sku: Optional[str] = None,
        adjustment_type: Optional[str] = None,
    ) -> list[dict]:
        result = list(self._adjustments)
        if warehouse_code:
            result = [a for a in result if a["warehouse_code"] == warehouse_code]
        if sku:
            result = [a for a in result if a["sku"] == sku]
        if adjustment_type:
            result = [a for a in result if a["adjustment_type"] == adjustment_type]
        return result

    def inventory_summary(self) -> dict:
        """Summary: total SKUs, total units, by warehouse."""
        all_skus = set()
        total_units = 0
        by_warehouse = {}
        for wh_code, stock in self._inventory.items():
            wh_total = sum(stock.values())
            by_warehouse[wh_code] = {
                "sku_count": len(stock),
                "total_units": wh_total,
            }
            all_skus.update(stock.keys())
            total_units += wh_total
        return {
            "total_skus": len(all_skus),
            "total_units": total_units,
            "warehouse_count": len(self._warehouses),
            "by_warehouse": by_warehouse,
        }

    def low_stock_alerts(self, threshold: int = 10) -> list[dict]:
        """Find SKUs below threshold across warehouses."""
        alerts = []
        for wh_code, stock in self._inventory.items():
            for sku, qty in stock.items():
                if qty <= threshold:
                    alerts.append({
                        "warehouse_code": wh_code,
                        "sku": sku,
                        "quantity": qty,
                        "threshold": threshold,
                    })
        return sorted(alerts, key=lambda x: x["quantity"])
