"""Inventory alert and reorder suggestion service."""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ReorderStrategy(str, Enum):
    """Reorder point calculation strategies."""
    FIXED = "fixed"                # Fixed reorder point
    DEMAND_BASED = "demand_based"  # Based on average daily demand
    EOQ = "eoq"                    # Economic Order Quantity


@dataclass
class InventoryAlert:
    """Inventory alert."""
    sku: str
    product_title: str
    warehouse: str
    current_qty: int
    available_qty: int
    threshold: int
    level: AlertLevel
    message: str
    suggested_action: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "product_title": self.product_title,
            "warehouse": self.warehouse,
            "current_qty": self.current_qty,
            "available_qty": self.available_qty,
            "threshold": self.threshold,
            "level": self.level.value,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ReorderSuggestion:
    """Reorder suggestion for a product."""
    sku: str
    product_title: str
    current_stock: int
    reorder_point: int
    suggested_quantity: int
    estimated_cost: Decimal
    supplier_name: str
    lead_time_days: int
    urgency: AlertLevel
    strategy: ReorderStrategy

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "product_title": self.product_title,
            "current_stock": self.current_stock,
            "reorder_point": self.reorder_point,
            "suggested_quantity": self.suggested_quantity,
            "estimated_cost": float(self.estimated_cost),
            "supplier_name": self.supplier_name,
            "lead_time_days": self.lead_time_days,
            "urgency": self.urgency.value,
            "strategy": self.strategy.value,
        }


class InventoryAlertService:
    """Monitors inventory levels and generates alerts / reorder suggestions."""

    def __init__(self, safety_stock_days: int = 7):
        self.safety_stock_days = safety_stock_days
        self._alerts: list[InventoryAlert] = []

    def check_stock_levels(
        self,
        items: list[dict],
    ) -> list[InventoryAlert]:
        """Check stock levels and generate alerts.

        Each item dict should have:
            sku, title, warehouse, quantity, reserved, threshold
        """
        alerts = []
        for item in items:
            qty = item.get("quantity", 0)
            reserved = item.get("reserved", 0)
            available = max(0, qty - reserved)
            threshold = item.get("threshold", 10)
            sku = item.get("sku", "UNKNOWN")
            title = item.get("title", "")
            warehouse = item.get("warehouse", "default")

            if available == 0:
                alert = InventoryAlert(
                    sku=sku,
                    product_title=title,
                    warehouse=warehouse,
                    current_qty=qty,
                    available_qty=available,
                    threshold=threshold,
                    level=AlertLevel.CRITICAL,
                    message=f"OUT OF STOCK: {sku} has 0 available units",
                    suggested_action=f"Emergency reorder {sku} immediately",
                )
                alerts.append(alert)
            elif available <= threshold // 2:
                alert = InventoryAlert(
                    sku=sku,
                    product_title=title,
                    warehouse=warehouse,
                    current_qty=qty,
                    available_qty=available,
                    threshold=threshold,
                    level=AlertLevel.CRITICAL,
                    message=f"CRITICAL LOW: {sku} has only {available} units (threshold: {threshold})",
                    suggested_action=f"Reorder {sku} urgently — stock below 50% of threshold",
                )
                alerts.append(alert)
            elif available <= threshold:
                alert = InventoryAlert(
                    sku=sku,
                    product_title=title,
                    warehouse=warehouse,
                    current_qty=qty,
                    available_qty=available,
                    threshold=threshold,
                    level=AlertLevel.WARNING,
                    message=f"LOW STOCK: {sku} has {available} units (threshold: {threshold})",
                    suggested_action=f"Plan reorder for {sku}",
                )
                alerts.append(alert)

        self._alerts.extend(alerts)
        return alerts

    def calculate_reorder_point(
        self,
        avg_daily_demand: Decimal,
        lead_time_days: int,
        safety_stock_days: Optional[int] = None,
    ) -> int:
        """Calculate reorder point based on demand and lead time."""
        safety = safety_stock_days or self.safety_stock_days
        reorder_point = avg_daily_demand * (lead_time_days + safety)
        return int(reorder_point) + 1  # Round up

    def calculate_eoq(
        self,
        annual_demand: int,
        order_cost: Decimal,
        holding_cost_per_unit: Decimal,
    ) -> int:
        """Calculate Economic Order Quantity (EOQ).

        EOQ = sqrt(2 * D * S / H)
        D = annual demand, S = order cost, H = holding cost per unit per year
        """
        if holding_cost_per_unit <= 0:
            return annual_demand  # fallback
        import math
        eoq = math.sqrt(
            2 * float(annual_demand) * float(order_cost) / float(holding_cost_per_unit)
        )
        return max(1, int(eoq) + 1)

    def generate_reorder_suggestions(
        self,
        products: list[dict],
        strategy: ReorderStrategy = ReorderStrategy.DEMAND_BASED,
    ) -> list[ReorderSuggestion]:
        """Generate reorder suggestions for products below reorder point.

        Each product dict should have:
            sku, title, current_stock, avg_daily_demand, cost_price,
            supplier_name, lead_time_days
        """
        suggestions = []
        for p in products:
            current = p.get("current_stock", 0)
            avg_demand = Decimal(str(p.get("avg_daily_demand", 1)))
            lead_time = p.get("lead_time_days", 7)
            cost = Decimal(str(p.get("cost_price", 0)))
            sku = p.get("sku", "UNKNOWN")

            if strategy == ReorderStrategy.DEMAND_BASED:
                reorder_point = self.calculate_reorder_point(avg_demand, lead_time)
                suggested_qty = int(avg_demand * 30)  # 30-day supply
            elif strategy == ReorderStrategy.EOQ:
                annual_demand = int(avg_demand * 365)
                order_cost = Decimal(str(p.get("order_cost", "50")))
                holding_pct = Decimal("0.25")  # 25% of cost
                holding_cost = cost * holding_pct
                reorder_point = self.calculate_reorder_point(avg_demand, lead_time)
                suggested_qty = self.calculate_eoq(annual_demand, order_cost, holding_cost)
            else:  # FIXED
                reorder_point = p.get("reorder_point", 10)
                suggested_qty = p.get("reorder_quantity", 100)

            if current <= reorder_point:
                urgency = AlertLevel.CRITICAL if current == 0 else (
                    AlertLevel.WARNING if current < reorder_point // 2
                    else AlertLevel.INFO
                )
                suggestions.append(ReorderSuggestion(
                    sku=sku,
                    product_title=p.get("title", ""),
                    current_stock=current,
                    reorder_point=reorder_point,
                    suggested_quantity=suggested_qty,
                    estimated_cost=(cost * suggested_qty).quantize(Decimal("0.01")),
                    supplier_name=p.get("supplier_name", "Unknown"),
                    lead_time_days=lead_time,
                    urgency=urgency,
                    strategy=strategy,
                ))

        # Sort by urgency (critical first)
        priority = {AlertLevel.CRITICAL: 0, AlertLevel.WARNING: 1, AlertLevel.INFO: 2}
        suggestions.sort(key=lambda s: priority.get(s.urgency, 9))
        return suggestions

    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        limit: int = 50,
    ) -> list[InventoryAlert]:
        """Get alert history."""
        items = self._alerts
        if level:
            items = [a for a in items if a.level == level]
        return items[-limit:]

    def clear_alerts(self) -> int:
        """Clear all alerts, return count cleared."""
        count = len(self._alerts)
        self._alerts.clear()
        return count


# Module-level singleton
inventory_alert_service = InventoryAlertService()
