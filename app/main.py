"""CrossBorder-ERP-Lite v2.0 — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.api import products, orders, dashboard, suppliers, inventory
from app.api import purchase_orders, auth_routes, reports
from app.api import warehouse, returns, customers
from app.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="4.0.0",
    description="Lightweight ERP for cross-border e-commerce sellers — "
                "products, orders, inventory, suppliers, shipping, reports, "
                "warehouse management, returns/refunds, customer CRM & analytics",
    lifespan=lifespan,
)

# Rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=120, burst=20)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(suppliers.router, prefix="/api/v1")
app.include_router(purchase_orders.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(warehouse.router, prefix="/api/v1")
app.include_router(returns.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name, "version": "4.0.0"}
