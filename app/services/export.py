"""Data export service — CSV, JSON, Excel-compatible."""

import csv
import io
import json
from datetime import datetime
from decimal import Decimal
from typing import Any


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class ExportService:
    """Export data in various formats."""

    @staticmethod
    def to_csv(rows: list[dict], columns: list[str] | None = None) -> str:
        if not rows:
            return ""
        cols = columns or list(rows[0].keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = {k: (float(v) if isinstance(v, Decimal) else v) for k, v in row.items()}
            writer.writerow(clean)
        return buf.getvalue()

    @staticmethod
    def to_json(rows: list[dict], pretty: bool = False) -> str:
        indent = 2 if pretty else None
        return json.dumps(rows, cls=DecimalEncoder, ensure_ascii=False, indent=indent)

    @staticmethod
    def to_tsv(rows: list[dict], columns: list[str] | None = None) -> str:
        """TSV format — Excel compatible when saved as .tsv."""
        if not rows:
            return ""
        cols = columns or list(rows[0].keys())
        lines = ["\t".join(cols)]
        for row in rows:
            vals = [str(row.get(c, "")) for c in cols]
            lines.append("\t".join(vals))
        return "\n".join(lines)

    @staticmethod
    def products_report(products: list[dict]) -> list[dict]:
        """Format product data for export."""
        return [
            {
                "SKU": p.get("sku", ""),
                "Title": p.get("title", ""),
                "Category": p.get("category", ""),
                "Cost Price": p.get("cost_price", 0),
                "Retail Price": p.get("retail_price", 0),
                "Margin %": (
                    round((float(p.get("retail_price", 0)) - float(p.get("cost_price", 0)))
                          / float(p.get("retail_price", 1)) * 100, 1)
                    if float(p.get("retail_price", 0)) > 0 else 0
                ),
                "Active": "Yes" if p.get("active", True) else "No",
            }
            for p in products
        ]

    @staticmethod
    def orders_report(orders: list[dict]) -> list[dict]:
        """Format order data for export."""
        return [
            {
                "Order #": o.get("order_number", ""),
                "Platform": o.get("platform", ""),
                "Status": o.get("status", ""),
                "Customer": o.get("customer_name", ""),
                "Subtotal": o.get("subtotal", 0),
                "Shipping": o.get("shipping_cost", 0),
                "Tax": o.get("tax", 0),
                "Total": o.get("total", 0),
                "Currency": o.get("currency", "USD"),
                "Tracking": o.get("tracking_number", ""),
                "Created": o.get("created_at", ""),
            }
            for o in orders
        ]
