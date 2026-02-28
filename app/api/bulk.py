"""Bulk import/export API endpoints."""

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import PlainTextResponse

from app.services.bulk_ops import BulkExporter, BulkImporter

router = APIRouter(prefix="/bulk", tags=["bulk"])
importer = BulkImporter()
exporter = BulkExporter()


@router.post("/import/products/csv")
async def import_products_csv(file: UploadFile = File(...)):
    """Bulk import products from a CSV file."""
    content = (await file.read()).decode("utf-8-sig")
    result = importer.import_products_csv(content)
    return {
        "summary": result.summary(),
        "errors": [
            {"row": e.row, "field": e.field, "message": e.message}
            for e in result.errors[:50]
        ],
        "duplicates": result.duplicates[:50],
        "sample_records": result.records[:5],
    }


@router.post("/import/products/json")
async def import_products_json(file: UploadFile = File(...)):
    """Bulk import products from a JSON file."""
    content = (await file.read()).decode("utf-8")
    result = importer.import_products_json(content)
    return {
        "summary": result.summary(),
        "errors": [
            {"row": e.row, "field": e.field, "message": e.message}
            for e in result.errors[:50]
        ],
        "duplicates": result.duplicates[:50],
        "sample_records": result.records[:5],
    }


@router.post("/import/orders/csv")
async def import_orders_csv(file: UploadFile = File(...)):
    """Bulk import orders from a CSV file."""
    content = (await file.read()).decode("utf-8-sig")
    result = importer.import_orders_csv(content)
    return {
        "summary": result.summary(),
        "errors": [
            {"row": e.row, "field": e.field, "message": e.message}
            for e in result.errors[:50]
        ],
    }


@router.get("/template/{entity}", response_class=PlainTextResponse)
async def download_template(entity: str = "products"):
    """Download a CSV import template (products or orders)."""
    if entity not in ("products", "orders"):
        return PlainTextResponse("Entity must be 'products' or 'orders'", status_code=400)
    template = exporter.generate_template(entity)
    return PlainTextResponse(
        template,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity}_template.csv"},
    )


@router.post("/export/products/csv", response_class=PlainTextResponse)
async def export_products_csv(products: list[dict]):
    """Export products to CSV."""
    csv_content = exporter.products_to_csv(products)
    return PlainTextResponse(
        csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products_export.csv"},
    )


@router.post("/export/products/json")
async def export_products_json(
    products: list[dict],
    pretty: bool = Query(True),
):
    """Export products to JSON."""
    json_content = exporter.products_to_json(products, pretty)
    return PlainTextResponse(
        json_content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=products_export.json"},
    )
