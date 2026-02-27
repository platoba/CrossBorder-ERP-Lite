# CrossBorder-ERP-Lite 🌏

Lightweight ERP for cross-border e-commerce sellers. Manage orders, inventory, and products across Amazon, Shopify, eBay, and AliExpress from a single dashboard.

## Features

- **Multi-Platform Orders** — Sync orders from Amazon SP-API, Shopify, eBay, AliExpress
- **Inventory Management** — Track stock levels, low-stock alerts, warehouse mapping
- **Product Catalog** — Centralized product database with multi-platform SKU mapping
- **Shipping Integration** — Calculate shipping costs, generate labels (4PX, YunExpress, Cainiao)
- **Financial Overview** — Revenue, costs, profit margins per product/platform
- **Supplier Management** — Track 1688/Alibaba suppliers, purchase orders, lead times
- **REST API** — Full API for automation and integration

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI
- **Database**: PostgreSQL 15
- **Cache**: Redis
- **Frontend**: Jinja2 + HTMX
- **Deployment**: Docker Compose

## Quick Start

```bash
git clone https://github.com/platoba/CrossBorder-ERP-Lite.git
cd CrossBorder-ERP-Lite
cp .env.example .env
docker compose up -d
open http://localhost:8001
```

## API Docs

- Swagger: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check app/ tests/
```

## Database Migrations

```bash
# Generate a new migration
alembic revision --autogenerate -m "description"
# Apply migrations
alembic upgrade head
```

## Architecture

```
┌──────────────┐     ┌──────────────┐
│  FastAPI     │────▶│  PostgreSQL  │
│  (API+Web)   │     └──────────────┘
└──────┬───────┘
       │         ┌──────────────┐
       ├────────▶│    Redis     │
       │         └──────────────┘
       │
       ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Amazon API  │  │  Shopify API │  │  eBay API    │
└──────────────┘  └──────────────┘  └──────────────┘
```

## License

MIT
