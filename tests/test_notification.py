"""Notification service tests."""

import pytest
from decimal import Decimal

from app.services.notification import (
    Notification,
    NotificationChannel,
    NotificationEvent,
    NotificationService,
)


class TestNotification:
    def test_create_notification(self):
        n = Notification(
            event=NotificationEvent.ORDER_CREATED,
            title="New Order",
            message="Order #123 created",
        )
        assert n.event == NotificationEvent.ORDER_CREATED
        assert n.delivered is False

    def test_to_dict(self):
        n = Notification(
            event=NotificationEvent.LOW_STOCK,
            title="Low Stock",
            message="SKU-001 low",
            data={"sku": "SKU-001", "qty": 5},
        )
        d = n.to_dict()
        assert d["event"] == "inventory.low_stock"
        assert d["data"]["sku"] == "SKU-001"
        assert "timestamp" in d

    def test_to_json(self):
        n = Notification(
            event=NotificationEvent.ORDER_SHIPPED,
            title="Shipped",
            message="Order shipped",
            data={"total": Decimal("29.99")},
        )
        json_str = n.to_json()
        assert '"total": 29.99' in json_str


class TestNotificationService:
    def test_notify_default_log(self):
        svc = NotificationService()
        results = svc.notify(
            NotificationEvent.ORDER_CREATED,
            "Test",
            "Test message",
        )
        assert len(results) == 1
        assert results[0].delivered is True
        assert results[0].channel == NotificationChannel.LOG

    def test_subscribe_and_notify(self):
        svc = NotificationService()
        received = []

        def handler(n):
            received.append(n)

        svc.register_handler(NotificationChannel.WEBHOOK, handler)
        svc.subscribe(
            NotificationEvent.ORDER_CREATED,
            [NotificationChannel.WEBHOOK, NotificationChannel.LOG],
        )

        results = svc.notify(
            NotificationEvent.ORDER_CREATED,
            "New Order",
            "Order #999",
        )
        assert len(results) == 2
        assert len(received) == 1
        assert received[0].title == "New Order"

    def test_notify_order_created(self):
        svc = NotificationService()
        results = svc.notify_order_created({
            "order_number": "ORD-TEST",
            "total": 49.99,
            "platform": "amazon",
        })
        assert len(results) >= 1
        assert "ORD-TEST" in results[0].title

    def test_notify_order_shipped(self):
        svc = NotificationService()
        results = svc.notify_order_shipped({
            "order_number": "ORD-SHIP",
            "tracking_number": "TRK123",
            "shipping_carrier": "4PX",
        })
        assert "🚚" in results[0].title

    def test_notify_low_stock(self):
        svc = NotificationService()
        results = svc.notify_low_stock({
            "sku": "SKU-LOW",
            "quantity": 3,
            "threshold": 10,
        })
        assert "⚠️" in results[0].title

    def test_notify_out_of_stock(self):
        svc = NotificationService()
        results = svc.notify_out_of_stock({"sku": "SKU-OOS"})
        assert "🔴" in results[0].title

    def test_handler_error_caught(self):
        svc = NotificationService()

        def bad_handler(n):
            raise RuntimeError("fail")

        svc.register_handler(NotificationChannel.WEBHOOK, bad_handler)
        svc.subscribe(NotificationEvent.ORDER_CREATED, [NotificationChannel.WEBHOOK])

        results = svc.notify(NotificationEvent.ORDER_CREATED, "Test", "msg")
        assert results[0].error == "fail"
        assert results[0].delivered is False

    def test_history(self):
        svc = NotificationService()
        svc.notify(NotificationEvent.ORDER_CREATED, "A", "msg a")
        svc.notify(NotificationEvent.LOW_STOCK, "B", "msg b")
        svc.notify(NotificationEvent.ORDER_CREATED, "C", "msg c")

        all_history = svc.get_history()
        assert len(all_history) == 3

        filtered = svc.get_history(event=NotificationEvent.ORDER_CREATED)
        assert len(filtered) == 2

    def test_stats(self):
        svc = NotificationService()
        svc.notify(NotificationEvent.ORDER_CREATED, "A", "a")
        svc.notify(NotificationEvent.ORDER_SHIPPED, "B", "b")

        stats = svc.stats()
        assert stats["total"] == 2
        assert stats["delivered"] == 2
        assert "order.created" in stats["by_event"]

    def test_history_max_limit(self):
        svc = NotificationService()
        svc._max_history = 5
        for i in range(10):
            svc.notify(NotificationEvent.ORDER_CREATED, f"N{i}", "msg")
        assert len(svc._history) == 5
