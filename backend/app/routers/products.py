from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.crud import get_all_products, search_products, create_product, update_product, delete_product, get_product_by_id

router = APIRouter(prefix="/api/products", tags=["products"])


class CreateProductRequest(BaseModel):
    name: str
    sku: str
    category: str
    unit: str
    unit_type: str = "continuous"
    price_default: float


class UpdateProductRequest(BaseModel):
    name: str
    price_default: float


@router.get("")
async def list_products() -> list[dict]:
    return get_all_products()


@router.get("/search")
async def search(q: str = Query("")) -> list[dict]:
    if not q:
        return []
    return search_products(q)


@router.post("")
async def create(body: CreateProductRequest) -> dict:
    product = create_product(body.name, body.sku, body.category, body.unit, body.unit_type, body.price_default)
    return product


@router.put("/{product_id}")
async def update(product_id: str, body: UpdateProductRequest) -> dict:
    existing = get_product_by_id(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    update_product(product_id, body.name, body.price_default)
    updated = get_product_by_id(product_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found after update")
    return updated


@router.delete("/{product_id}")
async def remove(product_id: str) -> dict[str, str]:
    existing = get_product_by_id(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    if not delete_product(product_id):
        raise HTTPException(status_code=400, detail="Cannot delete product that has existing orders")
    return {"status": "deleted"}
