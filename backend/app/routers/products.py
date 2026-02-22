from fastapi import APIRouter, Query

from app.crud import get_all_products, search_products

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products() -> list[dict]:
    return get_all_products()


@router.get("/search")
async def search(q: str = Query("")) -> list[dict]:
    if not q:
        return []
    return search_products(q)
