"""Tests for warehouse management service."""

import pytest

from app.services.warehouse import (
    AdjustmentRequest,
    TransferRequest,
    WarehouseInfo,
    WarehouseManager,
)


@pytest.fixture
def mgr():
    return WarehouseManager()


@pytest.fixture
def mgr_with_warehouses(mgr):
    mgr.create_warehouse(WarehouseInfo(code="SZ-01", name="Shenzhen Main", country="CN", city="Shenzhen"))
    mgr.create_warehouse(WarehouseInfo(code="LA-01", name="Los Angeles FBA", warehouse_type="fba", country="US", city="Los Angeles"))
    mgr.create_warehouse(WarehouseInfo(code="DE-01", name="Frankfurt 3PL", warehouse_type="3pl", country="DE", city="Frankfurt"))
    return mgr


class TestWarehouseCRUD:
    def test_create_warehouse(self, mgr):
        wh = mgr.create_warehouse(WarehouseInfo(code="WH-001", name="Test Warehouse"))
        assert wh.code == "WH-001"
        assert wh.name == "Test Warehouse"
        assert wh.id is not None

    def test_create_warehouse_all_fields(self, mgr):
        wh = mgr.create_warehouse(WarehouseInfo(
            code="WH-002", name="Full Warehouse", warehouse_type="3pl",
            country="US", city="New York", address="123 Main St",
            contact_name="John", contact_phone="+1234", capacity_units=5000,
        ))
        assert wh.warehouse_type == "3pl"
        assert wh.country == "US"
        assert wh.capacity_units == 5000

    def test_create_invalid_type(self, mgr):
        with pytest.raises(ValueError, match="Invalid warehouse type"):
            mgr.create_warehouse(WarehouseInfo(code="X", name="X", warehouse_type="invalid"))

    def test_create_empty_code(self, mgr):
        with pytest.raises(ValueError, match="required"):
            mgr.create_warehouse(WarehouseInfo(code="", name="Test"))

    def test_create_empty_name(self, mgr):
        with pytest.raises(ValueError, match="required"):
            mgr.create_warehouse(WarehouseInfo(code="WH", name=""))

    def test_get_warehouse(self, mgr_with_warehouses):
        wh = mgr_with_warehouses.get_warehouse("SZ-01")
        assert wh is not None
        assert wh.name == "Shenzhen Main"

    def test_get_nonexistent(self, mgr):
        assert mgr.get_warehouse("NOPE") is None

    def test_list_warehouses(self, mgr_with_warehouses):
        all_wh = mgr_with_warehouses.list_warehouses()
        assert len(all_wh) == 3

    def test_list_by_type(self, mgr_with_warehouses):
        fba = mgr_with_warehouses.list_warehouses(warehouse_type="fba")
        assert len(fba) == 1
        assert fba[0].code == "LA-01"

    def test_list_by_country(self, mgr_with_warehouses):
        cn = mgr_with_warehouses.list_warehouses(country="CN")
        assert len(cn) == 1

    def test_deactivate(self, mgr_with_warehouses):
        assert mgr_with_warehouses.deactivate_warehouse("SZ-01")
        active = mgr_with_warehouses.list_warehouses(active_only=True)
        assert all(w.code != "SZ-01" for w in active)

    def test_deactivate_nonexistent(self, mgr):
        assert not mgr.deactivate_warehouse("NOPE")

    def test_list_includes_inactive(self, mgr_with_warehouses):
        mgr_with_warehouses.deactivate_warehouse("SZ-01")
        all_wh = mgr_with_warehouses.list_warehouses(active_only=False)
        assert len(all_wh) == 3


class TestStockManagement:
    def test_set_and_get_stock(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        assert mgr_with_warehouses.get_stock("SZ-01", "SKU-001") == 100

    def test_get_stock_default_zero(self, mgr_with_warehouses):
        assert mgr_with_warehouses.get_stock("SZ-01", "NONEXIST") == 0

    def test_negative_stock_clamps_to_zero(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", -5)
        assert mgr_with_warehouses.get_stock("SZ-01", "SKU-001") == 0

    def test_warehouse_stock(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 50)
        mgr_with_warehouses.set_stock("SZ-01", "SKU-002", 30)
        stock = mgr_with_warehouses.get_warehouse_stock("SZ-01")
        assert stock == {"SKU-001": 50, "SKU-002": 30}

    def test_total_stock_across_warehouses(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 50)
        mgr_with_warehouses.set_stock("LA-01", "SKU-001", 25)
        total = mgr_with_warehouses.get_total_stock("SKU-001")
        assert total == {"SZ-01": 50, "LA-01": 25}

    def test_total_stock_not_in_all(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 50)
        total = mgr_with_warehouses.get_total_stock("SKU-001")
        assert "LA-01" not in total


class TestStockTransfer:
    def test_create_transfer(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        t = mgr_with_warehouses.create_transfer(TransferRequest(
            source_warehouse="SZ-01", dest_warehouse="LA-01",
            items=[{"sku": "SKU-001", "quantity": 20}],
        ))
        assert t["status"] == "draft"
        assert t["total_units"] == 20
        assert t["transfer_number"].startswith("TRF-")

    def test_transfer_same_warehouse(self, mgr_with_warehouses):
        with pytest.raises(ValueError, match="different"):
            mgr_with_warehouses.create_transfer(TransferRequest(
                source_warehouse="SZ-01", dest_warehouse="SZ-01",
                items=[{"sku": "SKU-001", "quantity": 10}],
            ))

    def test_transfer_nonexistent_source(self, mgr_with_warehouses):
        with pytest.raises(ValueError, match="not found"):
            mgr_with_warehouses.create_transfer(TransferRequest(
                source_warehouse="NOPE", dest_warehouse="LA-01",
                items=[{"sku": "SKU-001", "quantity": 10}],
            ))

    def test_transfer_empty_items(self, mgr_with_warehouses):
        with pytest.raises(ValueError, match="at least one"):
            mgr_with_warehouses.create_transfer(TransferRequest(
                source_warehouse="SZ-01", dest_warehouse="LA-01", items=[],
            ))

    def test_transfer_insufficient_stock(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 5)
        with pytest.raises(ValueError, match="Insufficient"):
            mgr_with_warehouses.create_transfer(TransferRequest(
                source_warehouse="SZ-01", dest_warehouse="LA-01",
                items=[{"sku": "SKU-001", "quantity": 10}],
            ))

    def test_full_transfer_lifecycle(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        t = mgr_with_warehouses.create_transfer(TransferRequest(
            source_warehouse="SZ-01", dest_warehouse="LA-01",
            items=[{"sku": "SKU-001", "quantity": 30}],
        ))
        # Approve (deducts)
        t = mgr_with_warehouses.approve_transfer(t["transfer_number"])
        assert t["status"] == "approved"
        assert mgr_with_warehouses.get_stock("SZ-01", "SKU-001") == 70

        # Ship
        t = mgr_with_warehouses.ship_transfer(t["transfer_number"], "TRACK123", "DHL")
        assert t["status"] == "in_transit"
        assert t["tracking_number"] == "TRACK123"

        # Receive (adds to dest)
        t = mgr_with_warehouses.receive_transfer(t["transfer_number"])
        assert t["status"] == "received"
        assert mgr_with_warehouses.get_stock("LA-01", "SKU-001") == 30

    def test_cancel_draft(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        t = mgr_with_warehouses.create_transfer(TransferRequest(
            source_warehouse="SZ-01", dest_warehouse="LA-01",
            items=[{"sku": "SKU-001", "quantity": 20}],
        ))
        t = mgr_with_warehouses.cancel_transfer(t["transfer_number"])
        assert t["status"] == "cancelled"
        assert mgr_with_warehouses.get_stock("SZ-01", "SKU-001") == 100

    def test_cancel_approved_restores_stock(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        t = mgr_with_warehouses.create_transfer(TransferRequest(
            source_warehouse="SZ-01", dest_warehouse="LA-01",
            items=[{"sku": "SKU-001", "quantity": 20}],
        ))
        mgr_with_warehouses.approve_transfer(t["transfer_number"])
        assert mgr_with_warehouses.get_stock("SZ-01", "SKU-001") == 80
        mgr_with_warehouses.cancel_transfer(t["transfer_number"])
        assert mgr_with_warehouses.get_stock("SZ-01", "SKU-001") == 100

    def test_cancel_received_fails(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        t = mgr_with_warehouses.create_transfer(TransferRequest(
            source_warehouse="SZ-01", dest_warehouse="LA-01",
            items=[{"sku": "SKU-001", "quantity": 20}],
        ))
        mgr_with_warehouses.approve_transfer(t["transfer_number"])
        mgr_with_warehouses.receive_transfer(t["transfer_number"])
        with pytest.raises(ValueError, match="Cannot cancel"):
            mgr_with_warehouses.cancel_transfer(t["transfer_number"])

    def test_list_transfers(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 200)
        mgr_with_warehouses.create_transfer(TransferRequest(
            source_warehouse="SZ-01", dest_warehouse="LA-01",
            items=[{"sku": "SKU-001", "quantity": 10}],
        ))
        mgr_with_warehouses.create_transfer(TransferRequest(
            source_warehouse="SZ-01", dest_warehouse="DE-01",
            items=[{"sku": "SKU-001", "quantity": 15}],
        ))
        assert len(mgr_with_warehouses.list_transfers()) == 2
        assert len(mgr_with_warehouses.list_transfers(warehouse_code="LA-01")) == 1

    def test_get_transfer(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        t = mgr_with_warehouses.create_transfer(TransferRequest(
            source_warehouse="SZ-01", dest_warehouse="LA-01",
            items=[{"sku": "SKU-001", "quantity": 10}],
        ))
        assert mgr_with_warehouses.get_transfer(t["transfer_number"]) is not None
        assert mgr_with_warehouses.get_transfer("NOPE") is None


class TestStockAdjustment:
    def test_create_adjustment(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        adj = mgr_with_warehouses.create_adjustment(AdjustmentRequest(
            warehouse_code="SZ-01", sku="SKU-001",
            adjustment_type="damage", quantity_change=-5,
            reason="Broken in transit",
        ))
        assert adj["previous_quantity"] == 100
        assert adj["new_quantity"] == 95
        assert mgr_with_warehouses.get_stock("SZ-01", "SKU-001") == 95

    def test_adjustment_add(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 50)
        adj = mgr_with_warehouses.create_adjustment(AdjustmentRequest(
            warehouse_code="SZ-01", sku="SKU-001",
            adjustment_type="return", quantity_change=10,
        ))
        assert adj["new_quantity"] == 60

    def test_adjustment_clamps_to_zero(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 3)
        adj = mgr_with_warehouses.create_adjustment(AdjustmentRequest(
            warehouse_code="SZ-01", sku="SKU-001",
            adjustment_type="write_off", quantity_change=-10,
        ))
        assert adj["new_quantity"] == 0

    def test_invalid_type(self, mgr_with_warehouses):
        with pytest.raises(ValueError, match="Invalid adjustment type"):
            mgr_with_warehouses.create_adjustment(AdjustmentRequest(
                warehouse_code="SZ-01", sku="SKU-001",
                adjustment_type="invalid", quantity_change=-1,
            ))

    def test_zero_quantity(self, mgr_with_warehouses):
        with pytest.raises(ValueError, match="cannot be zero"):
            mgr_with_warehouses.create_adjustment(AdjustmentRequest(
                warehouse_code="SZ-01", sku="SKU-001",
                adjustment_type="audit", quantity_change=0,
            ))

    def test_list_adjustments(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        mgr_with_warehouses.set_stock("SZ-01", "SKU-002", 50)
        mgr_with_warehouses.create_adjustment(AdjustmentRequest(
            warehouse_code="SZ-01", sku="SKU-001", adjustment_type="damage", quantity_change=-2,
        ))
        mgr_with_warehouses.create_adjustment(AdjustmentRequest(
            warehouse_code="SZ-01", sku="SKU-002", adjustment_type="audit", quantity_change=5,
        ))
        assert len(mgr_with_warehouses.list_adjustments()) == 2
        assert len(mgr_with_warehouses.list_adjustments(sku="SKU-001")) == 1
        assert len(mgr_with_warehouses.list_adjustments(adjustment_type="audit")) == 1


class TestInventorySummary:
    def test_empty_summary(self, mgr):
        s = mgr.inventory_summary()
        assert s["total_skus"] == 0
        assert s["total_units"] == 0

    def test_summary(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 100)
        mgr_with_warehouses.set_stock("SZ-01", "SKU-002", 50)
        mgr_with_warehouses.set_stock("LA-01", "SKU-001", 25)
        s = mgr_with_warehouses.inventory_summary()
        assert s["total_skus"] == 2
        assert s["total_units"] == 175
        assert s["warehouse_count"] == 3

    def test_low_stock_alerts(self, mgr_with_warehouses):
        mgr_with_warehouses.set_stock("SZ-01", "SKU-001", 5)
        mgr_with_warehouses.set_stock("SZ-01", "SKU-002", 100)
        mgr_with_warehouses.set_stock("LA-01", "SKU-003", 8)
        alerts = mgr_with_warehouses.low_stock_alerts(threshold=10)
        assert len(alerts) == 2
        assert alerts[0]["quantity"] == 5  # sorted ascending
