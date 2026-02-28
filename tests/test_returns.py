"""Tests for returns & refunds management service."""

import pytest

from app.services.returns import ReturnsManager, ReturnRequestData


@pytest.fixture
def mgr():
    return ReturnsManager(restocking_fee_pct=0.0)


@pytest.fixture
def mgr_with_fee():
    return ReturnsManager(restocking_fee_pct=0.15)


def _make_return(mgr, **overrides):
    defaults = dict(
        order_number="ORD-001",
        reason="defective",
        return_type="refund",
        platform="amazon",
        customer_name="Test User",
        customer_email="test@example.com",
        items=[{"sku": "SKU-001", "quantity": 1, "unit_price": 29.99}],
    )
    defaults.update(overrides)
    return mgr.create_return(ReturnRequestData(**defaults))


class TestCreateReturn:
    def test_basic_create(self, mgr):
        ret = _make_return(mgr)
        assert ret["return_number"].startswith("RET-")
        assert ret["status"] == "requested"
        assert ret["refund_amount"] == 29.99
        assert ret["restocking_fee"] == 0.0

    def test_with_restocking_fee(self, mgr_with_fee):
        ret = _make_return(mgr_with_fee)
        assert ret["restocking_fee"] == round(29.99 * 0.15, 2)
        assert ret["refund_amount"] == round(29.99 - 29.99 * 0.15, 2)

    def test_multiple_items(self, mgr):
        ret = _make_return(mgr, items=[
            {"sku": "SKU-001", "quantity": 2, "unit_price": 10.0},
            {"sku": "SKU-002", "quantity": 1, "unit_price": 20.0},
        ])
        assert ret["refund_amount"] == 40.0

    def test_invalid_reason(self, mgr):
        with pytest.raises(ValueError, match="Invalid reason"):
            _make_return(mgr, reason="invalid_reason")

    def test_invalid_type(self, mgr):
        with pytest.raises(ValueError, match="Invalid return type"):
            _make_return(mgr, return_type="invalid")

    def test_empty_order_number(self, mgr):
        with pytest.raises(ValueError, match="Order number"):
            _make_return(mgr, order_number="")

    def test_empty_items(self, mgr):
        with pytest.raises(ValueError, match="(?i)at least one"):
            _make_return(mgr, items=[])

    def test_all_reasons(self, mgr):
        for reason in ReturnsManager.VALID_REASONS:
            ret = _make_return(mgr, reason=reason)
            assert ret["reason"] == reason

    def test_all_types(self, mgr):
        for rtype in ReturnsManager.VALID_TYPES:
            ret = _make_return(mgr, return_type=rtype, order_number=f"ORD-{rtype}")
            assert ret["return_type"] == rtype


class TestReturnLifecycle:
    def test_approve(self, mgr):
        ret = _make_return(mgr)
        approved = mgr.approve_return(ret["return_number"], "WH-01", "Looks legit")
        assert approved["status"] == "approved"
        assert approved["warehouse_code"] == "WH-01"
        assert approved["approved_at"] is not None

    def test_approve_nonexistent(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.approve_return("NOPE")

    def test_approve_already_approved(self, mgr):
        ret = _make_return(mgr)
        mgr.approve_return(ret["return_number"])
        with pytest.raises(ValueError, match="Cannot approve"):
            mgr.approve_return(ret["return_number"])

    def test_reject(self, mgr):
        ret = _make_return(mgr)
        rejected = mgr.reject_return(ret["return_number"], "Policy violation")
        assert rejected["status"] == "rejected"
        assert rejected["internal_notes"] == "Policy violation"
        assert rejected["closed_at"] is not None

    def test_reject_nonexistent(self, mgr):
        with pytest.raises(ValueError, match="not found"):
            mgr.reject_return("NOPE")

    def test_receive_item(self, mgr):
        ret = _make_return(mgr)
        mgr.approve_return(ret["return_number"])
        received = mgr.receive_item(ret["return_number"], "passed", "TRACK123", "UPS")
        assert received["status"] == "item_received"
        assert received["quality_check"] == "passed"
        assert received["return_tracking"] == "TRACK123"

    def test_receive_without_approval(self, mgr):
        ret = _make_return(mgr)
        with pytest.raises(ValueError, match="Cannot receive"):
            mgr.receive_item(ret["return_number"])

    def test_receive_invalid_qc(self, mgr):
        ret = _make_return(mgr)
        mgr.approve_return(ret["return_number"])
        with pytest.raises(ValueError, match="Invalid QC"):
            mgr.receive_item(ret["return_number"], qc_status="bogus")

    def test_process_refund(self, mgr):
        ret = _make_return(mgr)
        mgr.approve_return(ret["return_number"])
        mgr.receive_item(ret["return_number"])
        refunded = mgr.process_refund(ret["return_number"])
        assert refunded["status"] == "refunded"
        assert refunded["refunded_at"] is not None

    def test_process_refund_custom_amount(self, mgr):
        ret = _make_return(mgr)
        mgr.approve_return(ret["return_number"])
        mgr.receive_item(ret["return_number"])
        refunded = mgr.process_refund(ret["return_number"], actual_refund=15.0, return_shipping_cost=5.0)
        assert refunded["refund_amount"] == 15.0
        assert refunded["return_shipping_cost"] == 5.0

    def test_refund_without_receive(self, mgr):
        ret = _make_return(mgr)
        mgr.approve_return(ret["return_number"])
        with pytest.raises(ValueError, match="Cannot refund"):
            mgr.process_refund(ret["return_number"])

    def test_close_after_refund(self, mgr):
        ret = _make_return(mgr)
        mgr.approve_return(ret["return_number"])
        mgr.receive_item(ret["return_number"])
        mgr.process_refund(ret["return_number"])
        closed = mgr.close_return(ret["return_number"])
        assert closed["status"] == "closed"

    def test_close_after_rejection(self, mgr):
        ret = _make_return(mgr)
        mgr.reject_return(ret["return_number"])
        closed = mgr.close_return(ret["return_number"])
        assert closed["status"] == "closed"

    def test_close_without_refund(self, mgr):
        ret = _make_return(mgr)
        with pytest.raises(ValueError, match="Cannot close"):
            mgr.close_return(ret["return_number"])

    def test_full_lifecycle(self, mgr):
        """Full happy path: create → approve → receive → refund → close."""
        ret = _make_return(mgr)
        mgr.approve_return(ret["return_number"], "WH-01")
        mgr.receive_item(ret["return_number"], "passed")
        mgr.process_refund(ret["return_number"])
        closed = mgr.close_return(ret["return_number"])
        assert closed["status"] == "closed"


class TestReturnQuery:
    def test_get_return(self, mgr):
        ret = _make_return(mgr)
        found = mgr.get_return(ret["return_number"])
        assert found is not None
        assert found["order_number"] == "ORD-001"

    def test_get_nonexistent(self, mgr):
        assert mgr.get_return("NOPE") is None

    def test_list_returns(self, mgr):
        _make_return(mgr, order_number="ORD-001")
        _make_return(mgr, order_number="ORD-002")
        _make_return(mgr, order_number="ORD-003", reason="wrong_item")
        assert len(mgr.list_returns()) == 3

    def test_list_by_status(self, mgr):
        r1 = _make_return(mgr, order_number="ORD-001")
        _make_return(mgr, order_number="ORD-002")
        mgr.approve_return(r1["return_number"])
        assert len(mgr.list_returns(status="approved")) == 1
        assert len(mgr.list_returns(status="requested")) == 1

    def test_list_by_order(self, mgr):
        _make_return(mgr, order_number="ORD-001")
        _make_return(mgr, order_number="ORD-002")
        assert len(mgr.list_returns(order_number="ORD-001")) == 1

    def test_list_by_platform(self, mgr):
        _make_return(mgr, platform="amazon")
        _make_return(mgr, platform="shopify", order_number="ORD-002")
        assert len(mgr.list_returns(platform="amazon")) == 1

    def test_list_by_reason(self, mgr):
        _make_return(mgr, reason="defective")
        _make_return(mgr, reason="wrong_item", order_number="ORD-002")
        assert len(mgr.list_returns(reason="defective")) == 1


class TestReturnStats:
    def test_empty_stats(self, mgr):
        s = mgr.stats()
        assert s["total"] == 0
        assert s["total_refunded"] == 0.0

    def test_stats(self, mgr):
        r1 = _make_return(mgr, order_number="ORD-001")
        r2 = _make_return(mgr, order_number="ORD-002", reason="wrong_item")
        mgr.approve_return(r1["return_number"])
        mgr.receive_item(r1["return_number"])
        mgr.process_refund(r1["return_number"])
        s = mgr.stats()
        assert s["total"] == 2
        assert s["by_status"]["refunded"] == 1
        assert s["by_reason"]["defective"] == 1
        assert s["by_reason"]["wrong_item"] == 1
        assert s["total_refunded"] == 29.99

    def test_return_rate(self, mgr):
        _make_return(mgr, order_number="ORD-001")
        _make_return(mgr, order_number="ORD-002")
        assert mgr.return_rate(100) == 2.0

    def test_return_rate_zero_orders(self, mgr):
        assert mgr.return_rate(0) == 0.0
