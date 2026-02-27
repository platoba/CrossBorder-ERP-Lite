"""Product CRUD API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Product
from app.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[ProductOut])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    active: bool | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Product)
    if active is not None:
        stmt = stmt.where(Product.active == active)
    if q:
        stmt = stmt.where(
            Product.title.ilike(f"%{q}%") | Product.sku.ilike(f"%{q}%")
        )
    stmt = stmt.order_by(Product.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ProductOut, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Product).where(Product.sku == data.sku))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Product with this SKU already exists")
    product = Product(**data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(product_id: UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(product, key, val)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    await db.delete(product)
    await db.commit()
