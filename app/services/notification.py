"""Notification service for order events.

Supports webhook, console logging, and pluggable notification channels.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Optional
import json
import logging

logger = logging.getLogger(__name__)


class NotificationEvent(str, Enum):
    """Order lifecycle events."""
    ORDER_CREATED = "order.created"
    ORDER_PAID = "order.paid"
    ORDER_SHIPPED = "order.shipped"
    ORDER_DELIVERED = "order.delivered"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_REFUNDED = "order.refunded"
    LOW_STOCK = "inventory.low_stock"
    OUT_OF_STOCK = "inventory.out_of_stock"
    PRICE_CHANGE = "product.price_change"
    NEW_SUPPLIER = "supplier.created"
    PO_RECEIVED = "purchase_order.received"


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    WEBHOOK = "webhook"
    LOG = "log"
    TELEGRAM = "telegram"
    EMAIL = "email"


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@dataclass
class Notification:
    """A single notification."""
    event: NotificationEvent
    title: str
    message: str
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    channel: NotificationChannel = NotificationChannel.LOG
    delivered: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event": self.event.value,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "channel": self.channel.value,
            "delivered": self.delivered,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), cls=DecimalEncoder)


class NotificationService:
    """Manages notification dispatch across channels."""

    def __init__(self):
        self._handlers: dict[NotificationChannel, list[Callable]] = {}
        self._history: list[Notification] = []
        self._subscriptions: dict[NotificationEvent, list[NotificationChannel]] = {}
        self._max_history = 1000

    def register_handler(
        self,
        channel: NotificationChannel,
        handler: Callable[[Notification], Any],
    ) -> None:
        """Register a handler for a notification channel."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

    def subscribe(
        self,
        event: NotificationEvent,
        channels: list[NotificationChannel],
    ) -> None:
        """Subscribe channels to specific events."""
        self._subscriptions[event] = channels

    def notify(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        data: Optional[dict] = None,
    ) -> list[Notification]:
        """Send notification to all subscribed channels for an event."""
        channels = self._subscriptions.get(
            event, [NotificationChannel.LOG]
        )
        results = []

        for channel in channels:
            notification = Notification(
                event=event,
                title=title,
                message=message,
                data=data or {},
                channel=channel,
            )

            handlers = self._handlers.get(channel, [])
            if not handlers:
                # Default: log handler
                self._default_log_handler(notification)
                notification.delivered = True
            else:
                for handler in handlers:
                    try:
                        handler(notification)
                        notification.delivered = True
                    except Exception as e:
                        notification.error = str(e)
                        logger.error(f"Notification failed: {channel.value} - {e}")

            self._history.append(notification)
            results.append(notification)

        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return results

    def notify_order_created(self, order_data: dict) -> list[Notification]:
        """Convenience: notify about new order."""
        order_num = order_data.get("order_number", "N/A")
        total = order_data.get("total", 0)
        platform = order_data.get("platform", "unknown")
        return self.notify(
            event=NotificationEvent.ORDER_CREATED,
            title=f"📦 New Order: {order_num}",
            message=f"New {platform} order #{order_num} — ${total}",
            data=order_data,
        )

    def notify_order_shipped(self, order_data: dict) -> list[Notification]:
        """Convenience: notify about shipped order."""
        order_num = order_data.get("order_number", "N/A")
        tracking = order_data.get("tracking_number", "")
        carrier = order_data.get("shipping_carrier", "")
        return self.notify(
            event=NotificationEvent.ORDER_SHIPPED,
            title=f"🚚 Order Shipped: {order_num}",
            message=f"Order #{order_num} shipped via {carrier} — {tracking}",
            data=order_data,
        )

    def notify_low_stock(self, product_data: dict) -> list[Notification]:
        """Convenience: notify about low stock."""
        sku = product_data.get("sku", "N/A")
        qty = product_data.get("quantity", 0)
        threshold = product_data.get("threshold", 10)
        return self.notify(
            event=NotificationEvent.LOW_STOCK,
            title=f"⚠️ Low Stock: {sku}",
            message=f"SKU {sku} has {qty} units (threshold: {threshold})",
            data=product_data,
        )

    def notify_out_of_stock(self, product_data: dict) -> list[Notification]:
        """Convenience: notify about out of stock."""
        sku = product_data.get("sku", "N/A")
        return self.notify(
            event=NotificationEvent.OUT_OF_STOCK,
            title=f"🔴 Out of Stock: {sku}",
            message=f"SKU {sku} is out of stock!",
            data=product_data,
        )

    def get_history(
        self,
        event: Optional[NotificationEvent] = None,
        channel: Optional[NotificationChannel] = None,
        limit: int = 50,
    ) -> list[Notification]:
        """Get notification history with optional filters."""
        items = self._history
        if event:
            items = [n for n in items if n.event == event]
        if channel:
            items = [n for n in items if n.channel == channel]
        return items[-limit:]

    def stats(self) -> dict:
        """Get notification statistics."""
        total = len(self._history)
        delivered = sum(1 for n in self._history if n.delivered)
        failed = sum(1 for n in self._history if n.error)
        by_event: dict[str, int] = {}
        by_channel: dict[str, int] = {}
        for n in self._history:
            by_event[n.event.value] = by_event.get(n.event.value, 0) + 1
            by_channel[n.channel.value] = by_channel.get(n.channel.value, 0) + 1
        return {
            "total": total,
            "delivered": delivered,
            "failed": failed,
            "by_event": by_event,
            "by_channel": by_channel,
        }

    @staticmethod
    def _default_log_handler(notification: Notification) -> None:
        """Default log-based handler."""
        logger.info(f"[{notification.event.value}] {notification.title}: {notification.message}")


# ── Webhook handler factory ─────────────────────────────

def create_webhook_handler(url: str, timeout: int = 10):
    """Create a webhook notification handler (sync, for use in background tasks)."""
    import httpx

    def handler(notification: Notification) -> None:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                url,
                json=notification.to_dict(),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()

    return handler


def create_telegram_handler(bot_token: str, chat_id: str):
    """Create a Telegram notification handler."""
    import httpx

    def handler(notification: Notification) -> None:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        text = f"*{notification.title}*\n{notification.message}"
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            })
            resp.raise_for_status()

    return handler


# Module-level singleton
notification_service = NotificationService()
