"""Product API tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_product(client: AsyncClient):
    payload = {
        "sku": "TEST-001",
        "title": "Test Widget",
        "cost_price": "5.00",
        "retail_price": "19.99",
    }
    resp = await client.post("/api/v1/products/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["sku"] == "TEST-001"
    assert data["title"] == "Test Widget"
    assert data["active"] is True


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient):
    # Create a product first
    await client.post("/api/v1/products/", json={"sku": "LIST-001", "title": "List Test"})
    resp = await client.get("/api/v1/products/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_duplicate_sku_rejected(client: AsyncClient):
    payload = {"sku": "DUP-001", "title": "First"}
    await client.post("/api/v1/products/", json=payload)
    resp = await client.post("/api/v1/products/", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/products/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient):
    # Create product first
    await client.post("/api/v1/products/", json={"sku": "ORD-SKU-001", "title": "Order Item"})
    order_payload = {
        "platform": "manual",
        "customer_name": "Test Customer",
        "items": [{"sku": "ORD-SKU-001", "quantity": 2, "unit_price": "10.00"}],
        "shipping_cost": "5.00",
        "tax": "1.50",
    }
    resp = await client.post("/api/v1/orders/", json=order_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "manual"
    assert float(data["total"]) == 26.50  # 2*10 + 5 + 1.5


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_products" in data
    assert "total_orders" in data


@pytest.mark.asyncio
async def test_create_supplier(client: AsyncClient):
    payload = {
        "name": "Test Supplier Co.",
        "platform": "1688",
        "contact_name": "Zhang Wei",
        "rating": 4,
        "lead_time_days": 5,
    }
    resp = await client.post("/api/v1/suppliers/", json=payload)
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test Supplier Co."
