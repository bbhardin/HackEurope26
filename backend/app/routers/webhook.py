import logging

from fastapi import APIRouter, BackgroundTasks, Query, Request, Response

from app.config import WHATSAPP_VERIFY_TOKEN
from app.whatsapp import parse_webhook_payload, process_incoming_message, IncomingMessage
from app.pipeline import handle_incoming_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("Webhook verification failed")
    return Response(content="Verification failed", status_code=403)


async def _process_and_handle(msg: IncomingMessage) -> None:
    try:
        processed = await process_incoming_message(msg)
        await handle_incoming_message(msg.sender_phone, processed.text, msg.message_type, processed.image_base64)
    except Exception as e:
        logger.error("Error processing message from %s: %s", msg.sender_phone, e)


@router.post("")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, str]:
    payload = await request.json()
    messages = parse_webhook_payload(payload)

    for msg in messages:
        background_tasks.add_task(_process_and_handle, msg)

    return {"status": "ok"}
