import base64
import logging
from dataclasses import dataclass

import httpx

from app.config import META_WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, OPENAI_API_KEY

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com/v21.0"


@dataclass
class IncomingMessage:
    sender_phone: str
    message_type: str  # "text" | "voice" | "image"
    text_body: str
    media_id: str
    raw_payload: dict


def parse_webhook_payload(payload: dict) -> list[IncomingMessage]:
    messages: list[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                sender = msg.get("from", "")
                msg_type = msg.get("type", "text")

                text_body = ""
                media_id = ""

                if msg_type == "text":
                    text_body = msg.get("text", {}).get("body", "")
                elif msg_type == "audio":
                    media_id = msg.get("audio", {}).get("id", "")
                    msg_type = "voice"
                elif msg_type == "image":
                    media_id = msg.get("image", {}).get("id", "")
                    caption = msg.get("image", {}).get("caption", "")
                    text_body = caption

                if not sender.startswith("+"):
                    sender = f"+{sender}"

                messages.append(IncomingMessage(
                    sender_phone=sender,
                    message_type=msg_type,
                    text_body=text_body,
                    media_id=media_id,
                    raw_payload=msg,
                ))
    return messages


async def download_media(media_id: str) -> bytes:
    async with httpx.AsyncClient() as client:
        url_resp = await client.get(
            f"{META_API_BASE}/{media_id}",
            headers={"Authorization": f"Bearer {META_WHATSAPP_TOKEN}"},
        )
        url_resp.raise_for_status()
        media_url = url_resp.json().get("url", "")

        media_resp = await client.get(
            media_url,
            headers={"Authorization": f"Bearer {META_WHATSAPP_TOKEN}"},
        )
        media_resp.raise_for_status()
        return media_resp.content


async def transcribe_voice(audio_bytes: bytes) -> str:
    if not OPENAI_API_KEY:
        logger.warning("No OPENAI_API_KEY set, returning placeholder transcription")
        return "[Voice message — transcription unavailable]"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            files={"file": ("audio.ogg", audio_bytes, "audio/ogg")},
            data={"model": "whisper-1"},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json().get("text", "")


async def image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


async def send_whatsapp_message(phone_number: str, message_text: str) -> bool:
    if not META_WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured, message not sent: %s", message_text[:100])
        return False

    clean_phone = phone_number.lstrip("+")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{META_API_BASE}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {META_WHATSAPP_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "text",
                "text": {"body": message_text},
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            logger.info("WhatsApp message sent to %s", phone_number)
            return True
        else:
            logger.error("WhatsApp send failed: %s %s", resp.status_code, resp.text)
            return False


@dataclass
class ProcessedMessage:
    text: str
    image_base64: str


async def process_incoming_message(msg: IncomingMessage) -> ProcessedMessage:
    if msg.message_type == "text":
        return ProcessedMessage(text=msg.text_body, image_base64="")

    if msg.message_type == "voice":
        try:
            audio_bytes = await download_media(msg.media_id)
            transcript = await transcribe_voice(audio_bytes)
            return ProcessedMessage(text=transcript, image_base64="")
        except Exception as e:
            logger.error("Voice processing failed: %s", e)
            return ProcessedMessage(text="[Voice message — processing failed]", image_base64="")

    if msg.message_type == "image":
        try:
            image_bytes = await download_media(msg.media_id)
            b64 = await image_to_base64(image_bytes)
            caption = msg.text_body or ""
            return ProcessedMessage(text=caption, image_base64=b64)
        except Exception as e:
            logger.error("Image processing failed: %s", e)
            caption = msg.text_body or "[Image — processing failed]"
            return ProcessedMessage(text=caption, image_base64="")

    return ProcessedMessage(text=msg.text_body or "[Unsupported message type]", image_base64="")
