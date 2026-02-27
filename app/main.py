"""CrossBorder-ERP-Lite — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.api import products, orders, dashboard, suppliers, inventory


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
    version="0.1.0",
    description="Lightweight ERP for cross-border e-commerce sellers",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(products.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(suppliers.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}
