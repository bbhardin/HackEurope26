from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.crud import (
    get_all_customers,
    get_customer_by_id,
    get_customer_context,
    get_customer_order_history,
    get_conversations,
    get_order_patterns,
    get_health_events,
    save_conversation,
    create_customer,
)
from app.orchestrator import send_manual_message, generate_suggested_messages

router = APIRouter(prefix="/api/customers", tags=["customers"])


class CreateCustomerRequest(BaseModel):
    name: str
    phone: str
    customer_type: str = "restaurant"
    address: str = "Not provided"


class MessageRequest(BaseModel):
    message: str


class NoteRequest(BaseModel):
    channel: str
    message: str
    order_id: Optional[str] = None


@router.get("")
async def list_customers() -> list[dict]:
    return get_all_customers()


@router.post("")
async def create_new_customer(body: CreateCustomerRequest) -> dict:
    customer = create_customer(body.name, body.phone, body.customer_type, body.address)
    return customer


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


@router.get("/{customer_id}/health-events")
async def health_events(customer_id: str) -> list[dict]:
    return get_health_events(customer_id, 20)


@router.post("/{customer_id}/message")
async def send_customer_message(customer_id: str, body: MessageRequest) -> dict:
    customer = get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return await send_manual_message(customer_id, body.message)


@router.post("/{customer_id}/note")
async def log_note(customer_id: str, body: NoteRequest) -> dict[str, str]:
    customer = get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    save_conversation(
        customer_id,
        "inbound",
        body.message,
        "manual_note",
        body.channel,
        "manual",
    )
    if body.order_id:
        from app.crud import create_alert
        create_alert("communication_note", customer_id, f"Note logged for order {body.order_id}: {body.message[:200]}")
    return {"status": "logged"}


@router.get("/{customer_id}/suggestions")
async def get_customer_suggestions(customer_id: str) -> list[str]:
    customer = get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return await generate_suggested_messages(customer_id)
