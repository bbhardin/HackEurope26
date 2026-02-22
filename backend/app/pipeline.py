import logging
import os
from datetime import datetime
from pathlib import Path

from app.config import DATABASE_PATH
from app.crud import (
    get_customer_by_phone,
    create_customer,
    save_conversation,
    create_alert,
    log_agent_action,
)
from app.customer_agent import run_customer_agent
from app.orchestrator import handle_agent_output
from app.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)

IMAGES_DIR = Path(DATABASE_PATH).parent / "images"


def _save_image(customer_id: str, image_base64: str) -> str:
    import base64
    customer_dir = IMAGES_DIR / customer_id
    customer_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = customer_dir / filename
    filepath.write_bytes(base64.b64decode(image_base64))
    return str(filepath.relative_to(IMAGES_DIR.parent))


async def handle_incoming_message(sender_phone: str, text_content: str, message_type: str, image_base64: str = "") -> None:
    customer = get_customer_by_phone(sender_phone)

    if not customer:
        logger.info("New customer from phone: %s — auto-creating profile", sender_phone)

        name = f"New Customer ({sender_phone})"
        for prefix in ["hi i'm ", "hi, i'm ", "hello i'm ", "hello, i'm ", "my name is "]:
            lower = text_content.lower()
            if prefix in lower:
                idx = lower.index(prefix) + len(prefix)
                extracted = text_content[idx:].split(",")[0].split(".")[0].split("\n")[0].strip()
                if extracted:
                    name = extracted
                break

        customer = create_customer(name, sender_phone)

        welcome = "Welcome! We've set up your account. Please let us know your name and delivery address, and we'll be happy to take your orders."
        await send_whatsapp_message(sender_phone, welcome)
        save_conversation(customer["id"], "outbound", welcome, "welcome_message")

        create_alert("new_customer", customer["id"], f"New customer profile created for {sender_phone}. Please review and update details.")
        log_agent_action("orchestrator", "customer_auto_created", "customer", customer["id"], {"phone": sender_phone, "name": name})

    image_url = ""
    if image_base64:
        try:
            image_url = _save_image(customer["id"], image_base64)
        except Exception as e:
            logger.error("Failed to save image: %s", e)

    save_conversation(customer["id"], "inbound", text_content or "[Image]", None, "whatsapp", "system")

    agent_output = await run_customer_agent(customer["id"], text_content, message_type, image_base64)

    if image_base64:
        agent_output["source"] = "image"

    log_agent_action(
        "customer_agent",
        "processed_message",
        "customer",
        customer["id"],
        {"intent": agent_output.get("intent", "unknown"), "message_preview": (text_content or "[Image]")[:200], "source": agent_output.get("source", "text")},
        agent_output.get("confidence"),
    )

    await handle_agent_output(customer, agent_output, text_content or "[Image]")
