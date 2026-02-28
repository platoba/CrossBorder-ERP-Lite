# CrossBorder-ERP-Lite v2.0

> Lightweight ERP for cross-border e-commerce sellers — manage products, orders, inventory, suppliers, shipping, and analytics from a single API.

[![CI](https://github.com/platoba/CrossBorder-ERP-Lite/actions/workflows/ci.yml/badge.svg)](https://github.com/platoba/CrossBorder-ERP-Lite/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Features

### Core ERP
- **Product Catalog** — SKU management, search, filtering, bulk operations
- **Order Management** — Multi-platform orders (Amazon, Shopify, eBay, AliExpress, TikTok, Walmart)
- **Inventory Tracking** — Multi-warehouse stock levels, reservations, low-stock alerts
- **Supplier Management** — 1688/Alibaba supplier database with ratings and lead times
- **Purchase Orders** — PO lifecycle (draft → sent → confirmed → shipped → received)

### Financial
- **Profit Calculator** — Full cost breakdown: product cost, intl shipping, platform fees, FBA, customs, VAT, returns
- **FX Rate Service** — Real-time currency conversion with caching (10+ currencies)
- **Break-even Analysis** — Automatic break-even price calculation per product

### Logistics
- **Shipping Rate Calculator** — 12 carriers (4PX, YunExpress, Yanwen, Cainiao, DHL, China Post, EMS, FedEx, UPS, SF Express)
- **11 Shipping Zones** — US, EU, UK, CA, AU, JP, SEA, SA, ME, AF, RU
- **Volumetric Weight** — Automatic dimensional weight calculation
- **Quote Comparison** — Cheapest/fastest shipping options

### Analytics & Reports
- **Profit Reports** — Per-product P&L with margin and ROI
- **Sales Trends** — Monthly order count, revenue, average order value
- **Inventory Health** — Stock status dashboard (ok/low/critical/out_of_stock)
- **Business Overview** — Top products, platform breakdown, comprehensive KPIs

### Operations
- **Notifications** — Order lifecycle events via webhook, Telegram, email, log
- **Inventory Alerts** — Low stock, out-of-stock, reorder suggestions
- **EOQ Calculator** — Economic Order Quantity for optimal reorder amounts
- **Rate Limiting** — Token bucket rate limiter with per-IP tracking
- **JWT Auth** — Secure API access with token-based authentication
- **Data Export** — CSV, JSON, TSV export with formatted reports

## Quick Start

```bash
# Clone
git clone https://github.com/platoba/CrossBorder-ERP-Lite.git
cd CrossBorder-ERP-Lite

# Install
pip install ".[dev]"

# Run (dev mode)
make run
# → http://localhost:8001/docs

# Run tests
make test

# Docker
make docker-up
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | JWT login |
| GET | `/api/v1/auth/me` | Current user |
| GET/POST | `/api/v1/products/` | List/Create products |
| GET/PATCH/DELETE | `/api/v1/products/{id}` | Get/Update/Delete product |
| GET/POST | `/api/v1/orders/` | List/Create orders |
| POST | `/api/v1/orders/{id}/ship` | Ship order |
| GET | `/api/v1/inventory/` | List inventory |
| POST | `/api/v1/inventory/{id}/adjust` | Adjust stock |
| GET/POST | `/api/v1/suppliers/` | List/Create suppliers |
| GET/POST | `/api/v1/purchase-orders/` | List/Create POs |
| POST | `/api/v1/purchase-orders/{id}/receive` | Receive PO |
| GET | `/api/v1/dashboard/stats` | Dashboard KPIs |
| GET | `/api/v1/reports/profit` | Profit analysis |
| GET | `/api/v1/reports/sales-trends` | Sales trends |
| GET | `/api/v1/reports/inventory-health` | Inventory health |
| GET | `/api/v1/reports/overview` | Business overview |

## Tech Stack

- **FastAPI** — Async Python web framework
- **SQLAlchemy 2.0** — Async ORM with PostgreSQL
- **Alembic** — Database migrations
- **Redis** — Caching & rate limiting
- **Docker Compose** — One-command deployment
- **GitHub Actions** — CI/CD pipeline

## Project Structure

```
app/
├── main.py              # FastAPI app entry point
├── config.py            # Pydantic settings
├── database.py          # Async SQLAlchemy engine
├── models/              # Database models (Product, Order, Inventory, Supplier, PO)
├── schemas/             # Pydantic request/response schemas
├── api/
│   ├── auth_routes.py   # Authentication endpoints
│   ├── products.py      # Product CRUD
│   ├── orders.py        # Order management
│   ├── inventory.py     # Stock tracking
│   ├── suppliers.py     # Supplier CRUD
│   ├── purchase_orders.py # PO management
│   ├── dashboard.py     # Dashboard stats
│   └── reports.py       # Analytics & reports
├── services/
│   ├── auth.py          # JWT authentication
│   ├── fx_rate.py       # Currency exchange
│   ├── export.py        # Data export (CSV/JSON/TSV)
│   ├── profit_calc.py   # Profit & margin calculator
│   ├── shipping.py      # Shipping rate calculator
│   ├── notification.py  # Event notifications
│   └── inventory_alert.py # Stock alerts & reorder
└── middleware/
    └── rate_limit.py    # Token bucket rate limiter
tests/                   # 83+ tests across 10 files
```

## License

MIT
