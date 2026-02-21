from fastapi import APIRouter, HTTPException

from app.crud import (
    get_all_customers,
    get_customer_by_id,
    get_customer_context,
    get_customer_order_history,
    get_conversations,
    get_order_patterns,
)

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
async def list_customers() -> list[dict]:
    return get_all_customers()


@router.get("/{customer_id}")
async def get_customer(customer_id: str) -> dict:
    customer = get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/{customer_id}/context")
async def get_context(customer_id: str) -> dict:
    ctx = get_customer_context(customer_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Customer context not found")
    return ctx


@router.get("/{customer_id}/orders")
async def get_orders(customer_id: str) -> list[dict]:
    return get_customer_order_history(customer_id, 20)


@router.get("/{customer_id}/conversations")
async def get_convos(customer_id: str) -> list[dict]:
    return get_conversations(customer_id, 30)


@router.get("/{customer_id}/patterns")
async def get_patterns(customer_id: str) -> list[dict]:
    return get_order_patterns(customer_id)
