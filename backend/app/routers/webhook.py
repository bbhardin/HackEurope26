import logging

from fastapi import APIRouter, Query, Request, Response

from app.config import WHATSAPP_VERIFY_TOKEN
from app.whatsapp import parse_webhook_payload, process_incoming_message
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


@router.post("")
async def receive_webhook(request: Request) -> dict[str, str]:
    payload = await request.json()
    messages = parse_webhook_payload(payload)

    for msg in messages:
        try:
            text_content = await process_incoming_message(msg)
            await handle_incoming_message(msg.sender_phone, text_content, msg.message_type)
        except Exception as e:
            logger.error("Error processing message from %s: %s", msg.sender_phone, e)

    return {"status": "ok"}
