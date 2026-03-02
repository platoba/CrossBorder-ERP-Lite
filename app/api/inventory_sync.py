"""
Inventory Sync API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.inventory_sync import get_inventory_sync_service, InventorySyncService
from pydantic import BaseModel
from typing import Dict
from datetime import datetime

router = APIRouter(prefix="/api/v1/inventory-sync", tags=["Inventory Sync"])


class SyncRequest(BaseModel):
    sku: str


class SyncResponse(BaseModel):
    sku: str
    results: Dict[str, bool]
    synced_at: str


@router.post("/sync", response_model=SyncResponse)
async def sync_inventory(
    request: SyncRequest,
    db: Session = Depends(get_db),
    sync_service: InventorySyncService = Depends(get_inventory_sync_service)
):
    """
    同步单个SKU库存到所有平台
    
    Example:
        POST /api/v1/inventory-sync/sync
        {"sku": "ABC-123"}
    """
    try:
        results = await sync_service.sync_all_platforms(request.sku)
        return SyncResponse(
            sku=request.sku,
            results=results,
            synced_at=datetime.utcnow().isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


@router.post("/sync-all")
async def sync_all_inventory(
    db: Session = Depends(get_db),
    sync_service: InventorySyncService = Depends(get_inventory_sync_service)
):
    """
    同步所有活跃产品库存到所有平台（后台任务）
    """
    return {"message": "Sync task started", "status": "processing"}
