"""Bulk import/export operations for products and orders.

Supports CSV and JSON formats with validation, duplicate detection,
and error reporting.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional


@dataclass
class ImportError:
    """Single import error record."""
    row: int
    field: str
    value: str
    message: str


@dataclass
class ImportResult:
    """Result of a bulk import operation."""
    total_rows: int = 0
    imported: int = 0
    skipped: int = 0
    errors: list[ImportError] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return round(self.imported / self.total_rows * 100, 1)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def summary(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "imported": self.imported,
            "skipped": self.skipped,
            "errors": len(self.errors),
            "duplicates": len(self.duplicates),
            "success_rate": self.success_rate,
        }


# ── Product field definitions ───────────────────────────

PRODUCT_FIELDS = {
    "sku": {"required": True, "type": "str", "max_length": 100},
    "title": {"required": True, "type": "str", "max_length": 500},
    "description": {"required": False, "type": "str", "max_length": 5000},
    "category": {"required": False, "type": "str", "max_length": 200},
    "brand": {"required": False, "type": "str", "max_length": 200},
    "weight_g": {"required": False, "type": "int", "min": 0, "max": 1000000},
    "cost_price": {"required": False, "type": "decimal", "min": 0},
    "retail_price": {"required": False, "type": "decimal", "min": 0},
    "image_url": {"required": False, "type": "str", "max_length": 1000},
    "active": {"required": False, "type": "bool", "default": True},
}

ORDER_FIELDS = {
    "platform": {"required": True, "type": "str", "choices": [
        "amazon", "shopify", "ebay", "aliexpress", "tiktok", "walmart", "manual",
    ]},
    "platform_order_id": {"required": False, "type": "str"},
    "customer_name": {"required": False, "type": "str", "max_length": 300},
    "customer_email": {"required": False, "type": "str", "max_length": 320},
    "subtotal": {"required": False, "type": "decimal", "min": 0},
    "shipping_cost": {"required": False, "type": "decimal", "min": 0},
    "tax": {"required": False, "type": "decimal", "min": 0},
    "total": {"required": False, "type": "decimal", "min": 0},
    "currency": {"required": False, "type": "str", "max_length": 3, "default": "USD"},
    "notes": {"required": False, "type": "str"},
}


class BulkValidator:
    """Validate individual fields against field definitions."""

    @staticmethod
    def validate_field(
        name: str,
        value: Any,
        spec: dict,
        row: int,
    ) -> tuple[Any, Optional[ImportError]]:
        """Validate and coerce a single field value."""
        ftype = spec.get("type", "str")
        required = spec.get("required", False)

        # Handle missing/empty
        if value is None or (isinstance(value, str) and value.strip() == ""):
            if required:
                return None, ImportError(row, name, "", f"Required field '{name}' is empty")
            return spec.get("default", "" if ftype == "str" else 0), None

        # Type coercion
        try:
            if ftype == "str":
                val = str(value).strip()
                max_len = spec.get("max_length")
                if max_len and len(val) > max_len:
                    return None, ImportError(row, name, val[:50], f"Exceeds max length {max_len}")
                choices = spec.get("choices")
                if choices and val.lower() not in [c.lower() for c in choices]:
                    return None, ImportError(row, name, val, f"Must be one of: {choices}")
                return val, None

            elif ftype == "int":
                val = int(float(value))
                mn, mx = spec.get("min"), spec.get("max")
                if mn is not None and val < mn:
                    return None, ImportError(row, name, str(val), f"Below minimum {mn}")
                if mx is not None and val > mx:
                    return None, ImportError(row, name, str(val), f"Above maximum {mx}")
                return val, None

            elif ftype == "decimal":
                val = Decimal(str(value))
                mn = spec.get("min")
                if mn is not None and val < Decimal(str(mn)):
                    return None, ImportError(row, name, str(val), f"Below minimum {mn}")
                return val, None

            elif ftype == "bool":
                if isinstance(value, bool):
                    return value, None
                sv = str(value).strip().lower()
                return sv in ("true", "1", "yes", "y", "on"), None

        except (ValueError, InvalidOperation, TypeError) as e:
            return None, ImportError(row, name, str(value)[:50], f"Invalid {ftype}: {e}")

        return value, None


class BulkImporter:
    """Import products and orders from CSV/JSON."""

    def __init__(self):
        self._validator = BulkValidator()

    # ── CSV Import ──────────────────────────────────────

    def import_products_csv(self, content: str, skip_header: bool = True) -> ImportResult:
        """Import products from CSV string."""
        return self._import_csv(content, PRODUCT_FIELDS, "sku", skip_header)

    def import_orders_csv(self, content: str, skip_header: bool = True) -> ImportResult:
        """Import orders from CSV string."""
        return self._import_csv(content, ORDER_FIELDS, "platform_order_id", skip_header)

    def _import_csv(
        self,
        content: str,
        field_defs: dict,
        dedup_key: str,
        skip_header: bool,
    ) -> ImportResult:
        result = ImportResult()
        reader = csv.DictReader(io.StringIO(content))

        seen_keys: set[str] = set()

        for row_num, row in enumerate(reader, start=2 if skip_header else 1):
            result.total_rows += 1
            record: dict = {}
            row_errors = []

            for fname, spec in field_defs.items():
                raw = row.get(fname)
                val, err = self._validator.validate_field(fname, raw, spec, row_num)
                if err:
                    row_errors.append(err)
                else:
                    record[fname] = val

            if row_errors:
                result.errors.extend(row_errors)
                result.skipped += 1
                continue

            # Dedup check
            dk = str(record.get(dedup_key, ""))
            if dk and dk in seen_keys:
                result.duplicates.append(dk)
                result.skipped += 1
                continue
            if dk:
                seen_keys.add(dk)

            result.records.append(record)
            result.imported += 1

        return result

    # ── JSON Import ─────────────────────────────────────

    def import_products_json(self, content: str) -> ImportResult:
        """Import products from JSON string (array of objects)."""
        return self._import_json(content, PRODUCT_FIELDS, "sku")

    def import_orders_json(self, content: str) -> ImportResult:
        """Import orders from JSON string (array of objects)."""
        return self._import_json(content, ORDER_FIELDS, "platform_order_id")

    def _import_json(
        self,
        content: str,
        field_defs: dict,
        dedup_key: str,
    ) -> ImportResult:
        result = ImportResult()
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            result.errors.append(ImportError(0, "", "", f"Invalid JSON: {e}"))
            return result

        if not isinstance(data, list):
            result.errors.append(ImportError(0, "", "", "JSON root must be an array"))
            return result

        seen_keys: set[str] = set()

        for row_num, item in enumerate(data, start=1):
            result.total_rows += 1
            if not isinstance(item, dict):
                result.errors.append(ImportError(row_num, "", "", "Each item must be an object"))
                result.skipped += 1
                continue

            record: dict = {}
            row_errors = []

            for fname, spec in field_defs.items():
                raw = item.get(fname)
                val, err = self._validator.validate_field(fname, raw, spec, row_num)
                if err:
                    row_errors.append(err)
                else:
                    record[fname] = val

            if row_errors:
                result.errors.extend(row_errors)
                result.skipped += 1
                continue

            dk = str(record.get(dedup_key, ""))
            if dk and dk in seen_keys:
                result.duplicates.append(dk)
                result.skipped += 1
                continue
            if dk:
                seen_keys.add(dk)

            result.records.append(record)
            result.imported += 1

        return result


class BulkExporter:
    """Export products and orders to CSV/JSON."""

    @staticmethod
    def products_to_csv(products: list[dict], columns: Optional[list[str]] = None) -> str:
        """Export products to CSV."""
        if not products:
            return ""
        cols = columns or list(PRODUCT_FIELDS.keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for p in products:
            clean = {}
            for k, v in p.items():
                if k in cols:
                    clean[k] = float(v) if isinstance(v, Decimal) else v
            writer.writerow(clean)
        return buf.getvalue()

    @staticmethod
    def products_to_json(products: list[dict], pretty: bool = True) -> str:
        """Export products to JSON."""
        def default(o):
            if isinstance(o, Decimal):
                return float(o)
            if isinstance(o, datetime):
                return o.isoformat()
            return str(o)

        return json.dumps(products, default=default, ensure_ascii=False, indent=2 if pretty else None)

    @staticmethod
    def orders_to_csv(orders: list[dict], columns: Optional[list[str]] = None) -> str:
        """Export orders to CSV."""
        if not orders:
            return ""
        cols = columns or list(ORDER_FIELDS.keys())
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for o in orders:
            clean = {}
            for k, v in o.items():
                if k in cols:
                    clean[k] = float(v) if isinstance(v, Decimal) else v
            writer.writerow(clean)
        return buf.getvalue()

    @staticmethod
    def generate_template(entity: str = "products") -> str:
        """Generate a CSV import template with headers and sample row."""
        if entity == "products":
            fields = PRODUCT_FIELDS
            sample = {
                "sku": "CB-EL-00001", "title": "Wireless Earbuds",
                "description": "Bluetooth 5.3", "category": "electronics",
                "brand": "MyBrand", "weight_g": "150",
                "cost_price": "12.50", "retail_price": "29.99",
                "image_url": "", "active": "true",
            }
        elif entity == "orders":
            fields = ORDER_FIELDS
            sample = {
                "platform": "amazon", "platform_order_id": "113-1234567-8901234",
                "customer_name": "John Doe", "customer_email": "john@example.com",
                "subtotal": "29.99", "shipping_cost": "4.99",
                "tax": "2.10", "total": "37.08",
                "currency": "USD", "notes": "",
            }
        else:
            return ""

        buf = io.StringIO()
        cols = list(fields.keys())
        writer = csv.DictWriter(buf, fieldnames=cols)
        writer.writeheader()
        writer.writerow(sample)
        return buf.getvalue()
