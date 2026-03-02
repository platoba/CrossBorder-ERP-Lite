"""
Tests for Inventory Sync Service
"""
import pytest
from app.inventory_sync import InventorySyncService
from app.models import Product, Inventory


@pytest.mark.asyncio
async def test_sync_all_platforms(db_session, sample_product):
    """测试多平台库存同步"""
    sync_service = InventorySyncService(db_session)
    
    # 创建库存记录
    inventory = Inventory(
        product_id=sample_product.id,
        warehouse_id=1,
        available_quantity=100,
        reserved_quantity=0
    )
    db_session.add(inventory)
    db_session.commit()
    
    # 执行同步
    results = await sync_service.sync_all_platforms(sample_product.sku)
    
    # 验证所有平台都同步成功
    assert results["amazon"] is True
    assert results["shopify"] is True
    assert results["ebay"] is True
    assert results["tiktok"] is True
    assert results["walmart"] is True


@pytest.mark.asyncio
async def test_sync_nonexistent_product(db_session):
    """测试同步不存在的产品"""
    sync_service = InventorySyncService(db_session)
    
    with pytest.raises(ValueError, match="Product .* not found"):
        await sync_service.sync_all_platforms("NONEXISTENT-SKU")


@pytest.mark.asyncio
async def test_sync_product_without_inventory(db_session, sample_product):
    """测试同步没有库存记录的产品"""
    sync_service = InventorySyncService(db_session)
    
    with pytest.raises(ValueError, match="Inventory for .* not found"):
        await sync_service.sync_all_platforms(sample_product.sku)
