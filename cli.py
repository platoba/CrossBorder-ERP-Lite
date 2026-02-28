"""CrossBorder-ERP-Lite CLI management tool.

Usage:
    python -m cli products list
    python -m cli products import products.csv
    python -m cli products export --format csv
    python -m cli orders list --status pending
    python -m cli sku generate --category electronics --count 5
    python -m cli sku map MYSKU-001 amazon AMZSKU001
    python -m cli analytics report --period monthly
    python -m cli analytics top-products --limit 10
    python -m cli bulk template products
    python -m cli shipping quote --weight 0.5 --country US
    python -m cli profit calc --price 29.99 --cost 45 --platform amazon
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from decimal import Decimal
from io import StringIO
from pathlib import Path

from app.services.analytics import AnalyticsEngine, Period
from app.services.bulk_ops import BulkExporter, BulkImporter
from app.services.profit_calc import CostBreakdown, ProfitCalculator
from app.services.shipping import ShippingService
from app.services.sku_manager import SKUManager


def main():
    parser = argparse.ArgumentParser(
        prog="erp-cli",
        description="CrossBorder-ERP-Lite CLI",
    )
    sub = parser.add_subparsers(dest="command", help="Top-level command")

    # ── SKU ──────────────────────────────────────────────
    sku_parser = sub.add_parser("sku", help="SKU management")
    sku_sub = sku_parser.add_subparsers(dest="action")

    gen = sku_sub.add_parser("generate", help="Generate SKUs")
    gen.add_argument("--category", default="", help="Product category")
    gen.add_argument("--count", type=int, default=1, help="How many SKUs")
    gen.add_argument("--prefix", default="CB", help="Brand prefix")
    gen.add_argument("--variant", default="", help="Variant code")

    parse = sku_sub.add_parser("parse", help="Parse a SKU")
    parse.add_argument("sku", help="SKU to parse")

    validate = sku_sub.add_parser("validate", help="Validate SKU for platform")
    validate.add_argument("sku", help="SKU to validate")
    validate.add_argument("--platform", required=True, help="Target platform")

    collisions = sku_sub.add_parser("collisions", help="Check SKU collisions")
    collisions.add_argument("skus", nargs="+", help="SKUs to check")

    # ── Shipping ─────────────────────────────────────────
    ship_parser = sub.add_parser("shipping", help="Shipping quotes")
    ship_sub = ship_parser.add_subparsers(dest="action")

    quote = ship_sub.add_parser("quote", help="Get shipping quotes")
    quote.add_argument("--weight", type=float, required=True, help="Weight in kg")
    quote.add_argument("--country", required=True, help="Destination country code")
    quote.add_argument("--carrier", nargs="*", help="Filter carriers")

    carriers = ship_sub.add_parser("carriers", help="List available carriers")
    carriers.add_argument("--country", required=True, help="Destination country")

    # ── Profit ───────────────────────────────────────────
    profit_parser = sub.add_parser("profit", help="Profit calculation")
    profit_sub = profit_parser.add_subparsers(dest="action")

    calc = profit_sub.add_parser("calc", help="Calculate profit")
    calc.add_argument("--price", type=float, required=True, help="Selling price (USD)")
    calc.add_argument("--cost", type=float, required=True, help="Product cost (CNY)")
    calc.add_argument("--shipping-intl", type=float, default=3.0, help="Intl shipping (USD)")
    calc.add_argument("--platform", default="amazon", help="Platform name")
    calc.add_argument("--ad-cost", type=float, default=0, help="Ad cost (USD)")
    calc.add_argument("--fba-fee", type=float, default=0, help="FBA fee (USD)")

    # ── Bulk ─────────────────────────────────────────────
    bulk_parser = sub.add_parser("bulk", help="Bulk import/export")
    bulk_sub = bulk_parser.add_subparsers(dest="action")

    template = bulk_sub.add_parser("template", help="Generate import template")
    template.add_argument("entity", choices=["products", "orders"], help="Entity type")
    template.add_argument("--output", "-o", help="Output file path")

    import_cmd = bulk_sub.add_parser("import", help="Import from file")
    import_cmd.add_argument("file", help="CSV or JSON file to import")
    import_cmd.add_argument("--entity", choices=["products", "orders"], default="products")

    # ── Analytics ────────────────────────────────────────
    analytics_parser = sub.add_parser("analytics", help="Sales analytics")
    analytics_sub = analytics_parser.add_subparsers(dest="action")

    report = analytics_sub.add_parser("report", help="Generate analytics report")
    report.add_argument("file", help="Orders JSON file")
    report.add_argument("--period", choices=["daily", "weekly", "monthly"], default="monthly")
    report.add_argument("--top", type=int, default=10, help="Top N products")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    handlers = {
        "sku": handle_sku,
        "shipping": handle_shipping,
        "profit": handle_profit,
        "bulk": handle_bulk,
        "analytics": handle_analytics,
    }
    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


# ── Command Handlers ────────────────────────────────────

def handle_sku(args):
    mgr = SKUManager(brand_prefix=getattr(args, "prefix", "CB"))

    if args.action == "generate":
        count = args.count
        skus = mgr.generate_batch(count, category=args.category)
        for sku in skus:
            print(sku)

    elif args.action == "parse":
        info = mgr.parse(args.sku)
        print(json.dumps({
            "raw": info.raw,
            "prefix": info.prefix,
            "category_code": info.category_code,
            "sequence": info.sequence,
            "variant": info.variant,
            "is_valid": info.is_valid,
            "format": info.format_name,
        }, indent=2))

    elif args.action == "validate":
        ok = mgr.validate_for_platform(args.sku, args.platform)
        status = "✅ Valid" if ok else "❌ Invalid"
        print(f"{status} for {args.platform}: {args.sku}")

    elif args.action == "collisions":
        pairs = mgr.check_collisions(args.skus)
        if pairs:
            print(f"⚠️  Found {len(pairs)} collision(s):")
            for a, b in pairs:
                print(f"  {a} ↔ {b}")
        else:
            print("✅ No collisions found")

    else:
        print("Usage: erp-cli sku {generate|parse|validate|collisions}")


def handle_shipping(args):
    svc = ShippingService()

    if args.action == "quote":
        quotes = svc.get_quotes(
            Decimal(str(args.weight)),
            args.country,
            carriers=args.carrier,
        )
        if not quotes:
            print("No carriers available for this route.")
            return
        print(f"{'Carrier':<15} {'Cost':<10} {'Days':<12} {'Tracking'}")
        print("-" * 50)
        for q in quotes:
            tracking = "✓" if q.tracking else "✗"
            print(f"{q.carrier:<15} ${q.cost_usd:<9} {q.estimated_days:<12} {tracking}")

    elif args.action == "carriers":
        available = svc.available_carriers(args.country)
        print(f"Carriers for {args.country}: {', '.join(available) or 'None'}")

    else:
        print("Usage: erp-cli shipping {quote|carriers}")


def handle_profit(args):
    if args.action == "calc":
        platform_fees = {
            "amazon": 15, "shopify": 2.9, "ebay": 13,
            "aliexpress": 8, "tiktok": 5, "walmart": 15,
        }
        fee = platform_fees.get(args.platform.lower(), 15)

        costs = CostBreakdown(
            product_cost=Decimal(str(args.cost)),
            shipping_intl=Decimal(str(args.shipping_intl)),
            platform_fee_pct=Decimal(str(fee)),
            ad_cost=Decimal(str(args.ad_cost)),
            fba_fee=Decimal(str(args.fba_fee)),
        )
        report = ProfitCalculator.calculate(Decimal(str(args.price)), costs)

        symbol = "✅" if report.is_profitable else "❌"
        print(f"{symbol} Profit Analysis for {args.platform.title()}")
        print(f"  Selling Price:   ${report.selling_price}")
        print(f"  Total Cost:      ${report.total_cost}")
        print(f"  Net Profit:      ${report.net_profit}")
        print(f"  Net Margin:      {report.net_margin_pct}%")
        print(f"  ROI:             {report.roi_pct}%")
        print(f"  Break-Even:      ${report.break_even_price}")
    else:
        print("Usage: erp-cli profit calc --price 29.99 --cost 45")


def handle_bulk(args):
    if args.action == "template":
        content = BulkExporter.generate_template(args.entity)
        if args.output:
            Path(args.output).write_text(content)
            print(f"Template saved to {args.output}")
        else:
            print(content)

    elif args.action == "import":
        path = Path(args.file)
        if not path.exists():
            print(f"File not found: {args.file}")
            sys.exit(1)

        content = path.read_text(encoding="utf-8-sig")
        imp = BulkImporter()

        if path.suffix.lower() == ".json":
            if args.entity == "products":
                result = imp.import_products_json(content)
            else:
                result = imp.import_orders_json(content)
        else:
            if args.entity == "products":
                result = imp.import_products_csv(content)
            else:
                result = imp.import_orders_csv(content)

        print(f"Import Summary:")
        for k, v in result.summary().items():
            print(f"  {k}: {v}")

        if result.errors:
            print(f"\nFirst 10 errors:")
            for e in result.errors[:10]:
                print(f"  Row {e.row}, {e.field}: {e.message}")

    else:
        print("Usage: erp-cli bulk {template|import}")


def handle_analytics(args):
    if args.action == "report":
        path = Path(args.file)
        if not path.exists():
            print(f"File not found: {args.file}")
            sys.exit(1)

        orders = json.loads(path.read_text())
        eng = AnalyticsEngine()
        period = Period(args.period)
        report = eng.generate_report(orders, period=period, top_n=args.top)
        report_dict = eng.report_to_dict(report)

        print(json.dumps(report_dict, indent=2, ensure_ascii=False))
    else:
        print("Usage: erp-cli analytics report orders.json")


if __name__ == "__main__":
    main()
