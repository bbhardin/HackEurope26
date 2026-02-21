import logging

from app.crud import (
    get_customer_by_phone,
    save_conversation,
    create_alert,
    log_agent_action,
)
from app.customer_agent import run_customer_agent
from app.orchestrator import handle_agent_output

logger = logging.getLogger(__name__)


async def handle_incoming_message(sender_phone: str, text_content: str, message_type: str) -> None:
    customer = get_customer_by_phone(sender_phone)

    if not customer:
        logger.warning("Unknown phone number: %s", sender_phone)
        create_alert("unknown_customer", None, f"Message from unknown number {sender_phone}: {text_content[:200]}")
        log_agent_action("orchestrator", "unknown_customer", "phone", sender_phone, {"message": text_content[:500]})
        return

    save_conversation(customer["id"], "inbound", text_content, None, "whatsapp")

    agent_output = await run_customer_agent(customer["id"], text_content, message_type)

    log_agent_action(
        "customer_agent",
        "processed_message",
        "customer",
        customer["id"],
        {"intent": agent_output.get("intent", "unknown"), "message_preview": text_content[:200]},
        agent_output.get("confidence"),
    )

    await handle_agent_output(customer, agent_output, text_content)
