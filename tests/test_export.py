"""Export service tests."""

import json
import pytest
from decimal import Decimal

from app.services.export import ExportService


class TestExportCSV:
    def test_basic_csv(self):
        rows = [
            {"name": "Widget", "price": 9.99, "qty": 10},
            {"name": "Gadget", "price": 19.99, "qty": 5},
        ]
        csv = ExportService.to_csv(rows)
        lines = csv.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
        assert "name,price,qty" in lines[0]

    def test_csv_with_columns(self):
        rows = [{"a": 1, "b": 2, "c": 3}]
        csv = ExportService.to_csv(rows, columns=["b", "a"])
        assert csv.startswith("b,a")

    def test_csv_decimal_handling(self):
        rows = [{"price": Decimal("29.99")}]
        csv = ExportService.to_csv(rows)
        assert "29.99" in csv

    def test_csv_empty(self):
        assert ExportService.to_csv([]) == ""


class TestExportJSON:
    def test_basic_json(self):
        rows = [{"name": "Test", "value": 42}]
        result = ExportService.to_json(rows)
        data = json.loads(result)
        assert data[0]["name"] == "Test"

    def test_json_pretty(self):
        rows = [{"name": "Test"}]
        result = ExportService.to_json(rows, pretty=True)
        assert "\n" in result

    def test_json_decimal(self):
        rows = [{"price": Decimal("19.99")}]
        result = ExportService.to_json(rows)
        data = json.loads(result)
        assert data[0]["price"] == 19.99


class TestExportTSV:
    def test_basic_tsv(self):
        rows = [{"a": 1, "b": 2}]
        tsv = ExportService.to_tsv(rows)
        lines = tsv.split("\n")
        assert "\t" in lines[0]
        assert len(lines) == 2

    def test_tsv_empty(self):
        assert ExportService.to_tsv([]) == ""


class TestProductsReport:
    def test_format_products(self):
        products = [
            {"sku": "SKU-1", "title": "Widget", "category": "Tools",
             "cost_price": 5.0, "retail_price": 19.99, "active": True},
        ]
        report = ExportService.products_report(products)
        assert len(report) == 1
        assert report[0]["SKU"] == "SKU-1"
        assert report[0]["Active"] == "Yes"
        assert report[0]["Margin %"] > 0

    def test_zero_retail_price(self):
        products = [{"sku": "Z", "title": "Z", "retail_price": 0, "cost_price": 0}]
        report = ExportService.products_report(products)
        assert report[0]["Margin %"] == 0


class TestOrdersReport:
    def test_format_orders(self):
        orders = [
            {"order_number": "ORD-001", "platform": "amazon", "status": "shipped",
             "customer_name": "John", "subtotal": 20, "shipping_cost": 5,
             "tax": 2, "total": 27, "currency": "USD", "tracking_number": "TRK1"},
        ]
        report = ExportService.orders_report(orders)
        assert report[0]["Order #"] == "ORD-001"
        assert report[0]["Total"] == 27
