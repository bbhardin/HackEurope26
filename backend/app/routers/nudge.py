from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.crud import (
    get_nudge_suggestions,
    get_nudge_suggestion_by_id,
    update_nudge_suggestion_status,
    save_conversation,
    log_agent_action,
)
from app.nudge_scheduler import run_nudge_scan
from app.whatsapp import send_whatsapp_message

router = APIRouter(prefix="/api/nudge", tags=["nudge"])


class SendNudgeRequest(BaseModel):
    custom_message: Optional[str] = None


@router.post("/run")
async def trigger_nudge_scan() -> dict:
    result = await run_nudge_scan()
    return result


@router.get("/suggestions")
async def list_suggestions(status: str = "pending") -> list[dict]:
    return get_nudge_suggestions(status)


@router.post("/suggestions/{nudge_id}/send")
async def send_nudge(nudge_id: str, body: SendNudgeRequest = SendNudgeRequest()) -> dict:
    nudge = get_nudge_suggestion_by_id(nudge_id)
    if not nudge:
        raise HTTPException(status_code=404, detail="Nudge suggestion not found")
    if nudge["status"] != "pending":
        raise HTTPException(status_code=400, detail="Nudge already processed")

    message = body.custom_message or nudge["suggested_message"]
    phone = nudge["contact_whatsapp"]

    await send_whatsapp_message(phone, message)
    save_conversation(nudge["customer_id"], "outbound", message, "reorder_nudge")
    update_nudge_suggestion_status(nudge_id, "sent")
    log_agent_action("wholesaler", "nudge_sent", "customer", nudge["customer_id"], {"nudge_id": nudge_id})

    return {"status": "sent"}


@router.post("/suggestions/{nudge_id}/dismiss")
async def dismiss_nudge(nudge_id: str) -> dict:
    nudge = get_nudge_suggestion_by_id(nudge_id)
    if not nudge:
        raise HTTPException(status_code=404, detail="Nudge suggestion not found")

    update_nudge_suggestion_status(nudge_id, "dismissed")
    return {"status": "dismissed"}
