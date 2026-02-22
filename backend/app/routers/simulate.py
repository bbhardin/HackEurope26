from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.pipeline import handle_incoming_message

router = APIRouter(prefix="/api/simulate", tags=["simulate"])


class SimulateMessage(BaseModel):
    phone: str
    message: str
    message_type: str = "text"


@router.post("/message")
async def simulate_incoming(body: SimulateMessage, background_tasks: BackgroundTasks) -> dict[str, str]:
    background_tasks.add_task(handle_incoming_message, body.phone, body.message, body.message_type)
    return {"status": "processing", "phone": body.phone}
