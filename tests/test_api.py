"""Extended API tests for v2.0."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_v2(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "4.0.0"


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
    assert data["active"] is True


@pytest.mark.asyncio
async def test_list_products(client: AsyncClient):
    await client.post("/api/v1/products/", json={"sku": "LIST-001", "title": "List Test"})
    resp = await client.get("/api/v1/products/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_search_products(client: AsyncClient):
    await client.post("/api/v1/products/", json={"sku": "SEARCH-1", "title": "Blue Widget"})
    await client.post("/api/v1/products/", json={"sku": "SEARCH-2", "title": "Red Gadget"})
    resp = await client.get("/api/v1/products/?q=Widget")
    assert resp.status_code == 200
    data = resp.json()
    assert any("Widget" in p["title"] for p in data)


@pytest.mark.asyncio
async def test_update_product(client: AsyncClient):
    create = await client.post("/api/v1/products/", json={"sku": "UPD-001", "title": "Old"})
    pid = create.json()["id"]
    resp = await client.patch(f"/api/v1/products/{pid}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient):
    create = await client.post("/api/v1/products/", json={"sku": "DEL-001", "title": "Delete Me"})
    pid = create.json()["id"]
    resp = await client.delete(f"/api/v1/products/{pid}")
    assert resp.status_code == 204


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
    assert float(data["total"]) == 26.50


@pytest.mark.asyncio
async def test_list_orders(client: AsyncClient):
    resp = await client.get("/api/v1/orders/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_filter_orders_by_platform(client: AsyncClient):
    await client.post("/api/v1/products/", json={"sku": "FILT-SKU", "title": "Filter"})
    await client.post("/api/v1/orders/", json={
        "platform": "manual",
        "items": [{"sku": "FILT-SKU", "quantity": 1, "unit_price": "10"}],
    })
    resp = await client.get("/api/v1/orders/?platform=manual")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_products" in data
    assert "total_orders" in data
    assert "low_stock_count" in data
    assert "total_suppliers" in data


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


@pytest.mark.asyncio
async def test_list_suppliers(client: AsyncClient):
    resp = await client.get("/api/v1/suppliers/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_supplier(client: AsyncClient):
    create = await client.post("/api/v1/suppliers/", json={"name": "Del Supplier"})
    sid = create.json()["id"]
    resp = await client.delete(f"/api/v1/suppliers/{sid}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_inventory_list(client: AsyncClient):
    resp = await client.get("/api/v1/inventory/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reports_overview(client: AsyncClient):
    resp = await client.get("/api/v1/reports/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_revenue" in data
    assert "total_orders" in data
    assert "top_products" in data


@pytest.mark.asyncio
async def test_reports_profit(client: AsyncClient):
    await client.post("/api/v1/products/", json={
        "sku": "PROFIT-1", "title": "Profit Test",
        "cost_price": "10.00", "retail_price": "29.99",
    })
    resp = await client.get("/api/v1/reports/profit")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reports_sales_trends(client: AsyncClient):
    resp = await client.get("/api/v1/reports/sales-trends")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reports_inventory_health(client: AsyncClient):
    resp = await client.get("/api/v1/reports/inventory-health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_auth_login_wrong_credentials(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "wrong@test.com", "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_auth_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
