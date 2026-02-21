from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.crud import (
    get_order_by_id,
    get_orders_by_status,
    get_all_orders,
    get_orders_overview,
)
from app.orchestrator import approve_order, reject_order, substitute_item

router = APIRouter(prefix="/api/orders", tags=["orders"])


class SubstituteRequest(BaseModel):
    item_id: str
    substitute_product_id: str


@router.get("")
async def list_orders(status: Optional[str] = Query(None), limit: int = Query(50)) -> list[dict]:
    if status:
        return get_orders_by_status(status)
    return get_all_orders(limit)


@router.get("/overview")
async def orders_overview() -> dict:
    return get_orders_overview()


@router.get("/{order_id}")
async def get_order(order_id: str) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/approve")
async def approve(order_id: str) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] not in ("pending_confirmation", "flagged"):
        raise HTTPException(status_code=400, detail=f"Cannot approve order with status '{order['status']}'")
    return await approve_order(order_id)


@router.post("/{order_id}/reject")
async def reject(order_id: str) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] not in ("pending_confirmation", "flagged"):
        raise HTTPException(status_code=400, detail=f"Cannot reject order with status '{order['status']}'")
    return await reject_order(order_id)


@router.post("/{order_id}/substitute")
async def substitute(order_id: str, body: SubstituteRequest) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    result = await substitute_item(order_id, body.item_id, body.substitute_product_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
