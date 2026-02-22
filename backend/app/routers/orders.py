from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.crud import (
    get_order_by_id,
    get_orders_by_status,
    get_all_orders,
    get_orders_overview,
    get_aggregated_items,
    update_order_items,
    log_agent_action,
    search_products,
)
from app.orchestrator import approve_order, reject_order, fulfil_order, substitute_item, send_manual_message, send_clarification

router = APIRouter(prefix="/api/orders", tags=["orders"])


class SubstituteRequest(BaseModel):
    item_id: str
    substitute_product_id: str


class MessageRequest(BaseModel):
    message: str


class FulfilRequest(BaseModel):
    message: str = ""


class ClarifyRequest(BaseModel):
    message: str


class UpdateOrderItem(BaseModel):
    product_id: str
    quantity: float
    unit_price: float


class UpdateOrderRequest(BaseModel):
    items: list[UpdateOrderItem]


@router.get("")
async def list_orders(status: Optional[str] = Query(None), limit: int = Query(50)) -> list[dict]:
    if status:
        return get_orders_by_status(status)
    return get_all_orders(limit)


@router.get("/overview")
async def orders_overview() -> dict:
    return get_orders_overview()


@router.get("/aggregate")
async def aggregate_items(status: str = Query("confirmed")) -> list[dict]:
    statuses = [s.strip() for s in status.split(",")]
    return get_aggregated_items(statuses)


@router.get("/{order_id}")
async def get_order(order_id: str) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}")
async def update_order(order_id: str, body: UpdateOrderRequest) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_items = order.get("items", [])
    new_items = [{"product_id": i.product_id, "quantity": i.quantity, "unit_price": i.unit_price} for i in body.items]
    update_order_items(order_id, new_items)

    log_agent_action(
        "wholesaler",
        "manual_edit",
        "order",
        order_id,
        {"old_item_count": len(old_items), "new_item_count": len(new_items)},
    )
    updated = get_order_by_id(order_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found after update")
    return updated


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
    if order["status"] not in ("pending_confirmation", "flagged", "needs_clarification"):
        raise HTTPException(status_code=400, detail=f"Cannot reject order with status '{order['status']}'")
    return await reject_order(order_id)


@router.post("/{order_id}/fulfil")
async def fulfil(order_id: str, body: FulfilRequest = FulfilRequest()) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order["status"] != "confirmed":
        raise HTTPException(status_code=400, detail=f"Cannot fulfil order with status '{order['status']}'")
    return await fulfil_order(order_id, body.message)


@router.post("/{order_id}/substitute")
async def substitute(order_id: str, body: SubstituteRequest) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    result = await substitute_item(order_id, body.item_id, body.substitute_product_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{order_id}/message")
async def send_order_message(order_id: str, body: MessageRequest) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return await send_manual_message(order["customer_id"], body.message, order_id)


@router.post("/{order_id}/clarify")
async def clarify(order_id: str, body: ClarifyRequest) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return await send_clarification(order_id, body.message)
