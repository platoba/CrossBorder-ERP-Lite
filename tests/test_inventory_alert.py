"""Inventory alert service tests."""

import pytest
from decimal import Decimal

from app.services.inventory_alert import (
    AlertLevel,
    InventoryAlertService,
    ReorderStrategy,
)


class TestCheckStockLevels:
    def test_out_of_stock_alert(self):
        svc = InventoryAlertService()
        items = [{"sku": "OOS-1", "title": "Widget", "warehouse": "US",
                  "quantity": 0, "reserved": 0, "threshold": 10}]
        alerts = svc.check_stock_levels(items)
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.CRITICAL
        assert "OUT OF STOCK" in alerts[0].message

    def test_critical_low_alert(self):
        svc = InventoryAlertService()
        items = [{"sku": "LOW-1", "title": "Gadget", "warehouse": "US",
                  "quantity": 3, "reserved": 0, "threshold": 10}]
        alerts = svc.check_stock_levels(items)
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.CRITICAL

    def test_warning_alert(self):
        svc = InventoryAlertService()
        items = [{"sku": "WARN-1", "title": "Thing", "warehouse": "US",
                  "quantity": 8, "reserved": 0, "threshold": 10}]
        alerts = svc.check_stock_levels(items)
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.WARNING

    def test_no_alert_when_sufficient(self):
        svc = InventoryAlertService()
        items = [{"sku": "OK-1", "title": "Good", "warehouse": "US",
                  "quantity": 100, "reserved": 0, "threshold": 10}]
        alerts = svc.check_stock_levels(items)
        assert len(alerts) == 0

    def test_reserved_stock_considered(self):
        svc = InventoryAlertService()
        items = [{"sku": "RES-1", "title": "Reserved", "warehouse": "US",
                  "quantity": 20, "reserved": 18, "threshold": 10}]
        alerts = svc.check_stock_levels(items)
        assert len(alerts) == 1  # available = 2, threshold = 10

    def test_multiple_items(self):
        svc = InventoryAlertService()
        items = [
            {"sku": "A", "title": "A", "warehouse": "US", "quantity": 0, "reserved": 0, "threshold": 5},
            {"sku": "B", "title": "B", "warehouse": "US", "quantity": 100, "reserved": 0, "threshold": 5},
            {"sku": "C", "title": "C", "warehouse": "EU", "quantity": 3, "reserved": 0, "threshold": 5},
        ]
        alerts = svc.check_stock_levels(items)
        assert len(alerts) == 2  # A (OOS) and C (low)

    def test_alert_to_dict(self):
        svc = InventoryAlertService()
        items = [{"sku": "DICT-1", "title": "Test", "warehouse": "US",
                  "quantity": 0, "reserved": 0, "threshold": 10}]
        alerts = svc.check_stock_levels(items)
        d = alerts[0].to_dict()
        assert d["sku"] == "DICT-1"
        assert d["level"] == "critical"


class TestReorderPoint:
    def test_basic_calculation(self):
        svc = InventoryAlertService(safety_stock_days=7)
        rp = svc.calculate_reorder_point(
            avg_daily_demand=Decimal("10"),
            lead_time_days=14,
        )
        assert rp == 211  # 10 * (14 + 7) + 1

    def test_custom_safety_stock(self):
        svc = InventoryAlertService()
        rp = svc.calculate_reorder_point(
            avg_daily_demand=Decimal("5"),
            lead_time_days=7,
            safety_stock_days=3,
        )
        assert rp == 51  # 5 * (7+3) + 1


class TestEOQ:
    def test_basic_eoq(self):
        svc = InventoryAlertService()
        eoq = svc.calculate_eoq(
            annual_demand=1000,
            order_cost=Decimal("50"),
            holding_cost_per_unit=Decimal("5"),
        )
        # sqrt(2*1000*50/5) = sqrt(20000) ≈ 141.4 → 142
        assert eoq == 142

    def test_zero_holding_cost(self):
        svc = InventoryAlertService()
        eoq = svc.calculate_eoq(
            annual_demand=1000,
            order_cost=Decimal("50"),
            holding_cost_per_unit=Decimal("0"),
        )
        assert eoq == 1000  # fallback to annual demand


class TestReorderSuggestions:
    def test_demand_based_suggestions(self):
        svc = InventoryAlertService()
        products = [
            {
                "sku": "REORDER-1",
                "title": "Widget",
                "current_stock": 5,
                "avg_daily_demand": 10,
                "cost_price": 5.0,
                "supplier_name": "Supplier A",
                "lead_time_days": 7,
            },
        ]
        suggestions = svc.generate_reorder_suggestions(products)
        assert len(suggestions) == 1
        assert suggestions[0].sku == "REORDER-1"
        assert suggestions[0].suggested_quantity == 300  # 10 * 30

    def test_no_suggestion_when_stocked(self):
        svc = InventoryAlertService()
        products = [
            {
                "sku": "FULL-1",
                "title": "Stocked",
                "current_stock": 500,
                "avg_daily_demand": 1,
                "cost_price": 10,
                "supplier_name": "S",
                "lead_time_days": 7,
            },
        ]
        suggestions = svc.generate_reorder_suggestions(products)
        assert len(suggestions) == 0

    def test_eoq_strategy(self):
        svc = InventoryAlertService()
        products = [
            {
                "sku": "EOQ-1",
                "title": "EOQ Item",
                "current_stock": 0,
                "avg_daily_demand": 5,
                "cost_price": 10,
                "order_cost": 100,
                "supplier_name": "S",
                "lead_time_days": 14,
            },
        ]
        suggestions = svc.generate_reorder_suggestions(
            products, strategy=ReorderStrategy.EOQ
        )
        assert len(suggestions) == 1
        assert suggestions[0].strategy == ReorderStrategy.EOQ

    def test_urgency_sorting(self):
        svc = InventoryAlertService()
        products = [
            {"sku": "A", "title": "A", "current_stock": 5, "avg_daily_demand": 3,
             "cost_price": 10, "supplier_name": "S", "lead_time_days": 7},
            {"sku": "B", "title": "B", "current_stock": 0, "avg_daily_demand": 3,
             "cost_price": 10, "supplier_name": "S", "lead_time_days": 7},
        ]
        suggestions = svc.generate_reorder_suggestions(products)
        assert suggestions[0].sku == "B"  # Critical (0 stock) first
        assert suggestions[0].urgency == AlertLevel.CRITICAL


class TestAlertHistory:
    def test_get_alerts(self):
        svc = InventoryAlertService()
        items = [
            {"sku": "H1", "title": "A", "warehouse": "US", "quantity": 0, "reserved": 0, "threshold": 5},
            {"sku": "H2", "title": "B", "warehouse": "US", "quantity": 3, "reserved": 0, "threshold": 5},
        ]
        svc.check_stock_levels(items)
        all_alerts = svc.get_alerts()
        assert len(all_alerts) == 2

        critical = svc.get_alerts(level=AlertLevel.CRITICAL)
        assert len(critical) == 1

    def test_clear_alerts(self):
        svc = InventoryAlertService()
        svc.check_stock_levels([
            {"sku": "X", "title": "X", "warehouse": "US", "quantity": 0, "reserved": 0, "threshold": 5}
        ])
        count = svc.clear_alerts()
        assert count == 1
        assert len(svc.get_alerts()) == 0
