"""Supplier CRUD API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Supplier
from app.schemas import SupplierCreate, SupplierOut

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("/", response_model=list[SupplierOut])
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Supplier).order_by(Supplier.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=SupplierOut, status_code=201)
async def create_supplier(data: SupplierCreate, db: AsyncSession = Depends(get_db)):
    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(supplier_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(404, "Supplier not found")
    return supplier


@router.delete("/{supplier_id}", status_code=204)
async def delete_supplier(supplier_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(404, "Supplier not found")
    await db.delete(supplier)
    await db.commit()
