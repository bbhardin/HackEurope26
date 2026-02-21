import logging

from app.crud import (
    create_order,
    get_customer_order_history,
    get_customer_context,
    save_conversation,
    log_agent_action,
    create_alert,
    update_order_status,
    update_order_items,
    get_order_by_id,
)
from app.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)


async def handle_agent_output(customer: dict, agent_output: dict, raw_message: str) -> None:
    intent = agent_output.get("intent", "general_inquiry")
    items = agent_output.get("items", [])
    anomalies = agent_output.get("anomalies", [])

    if intent in ("place_order", "repeat_order"):
        await _handle_order_intent(customer, agent_output, raw_message, items, anomalies)
    elif intent == "modify_order":
        await _handle_modify_intent(customer, agent_output, raw_message)
    elif intent == "remind_last_order":
        await _handle_remind_intent(customer, agent_output)
    else:
        await _handle_general_intent(customer, agent_output)


async def _handle_order_intent(
    customer: dict,
    agent_output: dict,
    raw_message: str,
    items: list[dict],
    anomalies: list[str],
) -> None:
    if not items:
        logger.warning("Order intent but no items parsed for customer %s", customer["id"])
        create_alert(
            "parse_failure",
            customer["id"],
            f"Order intent detected but no items could be parsed. Message: {raw_message[:200]}",
        )
        return

    order_items = []
    for item in items:
        order_items.append({
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "unit_price": item["unit_price"],
            "matched_confidence": item.get("matched_confidence", 0.9),
            "original_text": item.get("original_text", ""),
        })

    status = "pending_confirmation"
    if anomalies:
        status = "flagged"

    order = create_order(
        customer_id=customer["id"],
        raw_message=raw_message,
        items=order_items,
        status=status,
    )

    if anomalies:
        for anomaly in anomalies:
            create_alert("anomaly", customer["id"], f"Order {order['id']}: {anomaly}")

    notes = agent_output.get("notes", "")
    if notes:
        create_alert("agent_note", customer["id"], f"Order {order['id']}: {notes}")

    log_agent_action(
        "orchestrator",
        "order_created",
        "order",
        order["id"],
        {
            "intent": agent_output.get("intent"),
            "item_count": len(items),
            "total_value": order["total_value"],
            "anomalies": anomalies,
            "status": status,
        },
        agent_output.get("confidence"),
    )


async def _handle_modify_intent(customer: dict, agent_output: dict, raw_message: str) -> None:
    from app.crud import get_orders_by_status

    pending = get_orders_by_status("pending_confirmation")
    customer_pending = [o for o in pending if o["customer_id"] == customer["id"]]

    if not customer_pending:
        flagged = get_orders_by_status("flagged")
        customer_pending = [o for o in flagged if o["customer_id"] == customer["id"]]

    if not customer_pending:
        response = "You don't have any pending orders to modify. Would you like to place a new order?"
        await send_whatsapp_message(customer["contact_whatsapp"], response)
        save_conversation(customer["id"], "outbound", response, "modify_order_no_pending")
        return

    target_order = customer_pending[0]
    new_items = agent_output.get("items", [])

    if new_items:
        order_items = []
        for item in new_items:
            order_items.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "matched_confidence": item.get("matched_confidence", 0.9),
                "original_text": item.get("original_text", ""),
            })
        update_order_items(target_order["id"], order_items)

        log_agent_action(
            "orchestrator",
            "order_modified",
            "order",
            target_order["id"],
            {"new_items": len(new_items), "raw_message": raw_message[:200]},
            agent_output.get("confidence"),
        )
        create_alert(
            "order_modified",
            customer["id"],
            f"Order {target_order['id']} was modified by customer. Please re-review.",
        )
    else:
        create_alert(
            "modification_unclear",
            customer["id"],
            f"Customer requested modification but items unclear. Message: {raw_message[:200]}",
        )


async def _handle_remind_intent(customer: dict, agent_output: dict) -> None:
    response = agent_output.get("response_text", "")
    if not response:
        history = get_customer_order_history(customer["id"], 3)
        if history:
            last = history[0]
            lines = [f"Your most recent order ({last['created_at'][:10]}):"]
            for item in last.get("items", []):
                lines.append(f"  - {item['quantity']} {item['unit']} {item['product_name']} @ {item['unit_price']}/unit")
            lines.append(f"  Total: EUR {last['total_value']:.2f}")
            response = "\n".join(lines)
        else:
            response = "I couldn't find any recent orders for your account."

    await send_whatsapp_message(customer["contact_whatsapp"], response)
    save_conversation(customer["id"], "outbound", response, "remind_last_order")
    log_agent_action("orchestrator", "reminder_sent", "customer", customer["id"], {"response_preview": response[:200]})


async def _handle_general_intent(customer: dict, agent_output: dict) -> None:
    response = agent_output.get("response_text", "")
    if not response:
        response = "Thank you for your message. A member of our team will get back to you shortly."

    await send_whatsapp_message(customer["contact_whatsapp"], response)
    save_conversation(customer["id"], "outbound", response, "general_inquiry")
    log_agent_action("orchestrator", "general_response", "customer", customer["id"], {"response_preview": response[:200]})


def generate_confirmation_message(order: dict) -> str:
    customer_name = order.get("customer_name", "Customer")
    items = order.get("items", [])

    lines = [f"Order confirmed, {customer_name}:"]
    for item in items:
        name = item.get("product_name", item.get("product_id", "Unknown"))
        qty = item["quantity"]
        unit = item.get("unit", "")
        price = item["unit_price"]
        line_total = qty * price
        lines.append(f"  - {qty}{unit} {name} (EUR {price:.2f}/{unit}) — EUR {line_total:.2f}")

    lines.append(f"Total: EUR {order['total_value']:.2f}")
    lines.append("Delivery: Next business day before 10:00")
    return "\n".join(lines)


async def approve_order(order_id: str) -> dict:
    update_order_status(order_id, "confirmed", "wholesaler")
    order = get_order_by_id(order_id)
    if not order:
        return {"error": "Order not found"}

    confirmation = generate_confirmation_message(order)
    phone = order.get("customer_whatsapp", "")
    if phone:
        await send_whatsapp_message(phone, confirmation)
        save_conversation(order["customer_id"], "outbound", confirmation, "order_confirmed")

    log_agent_action(
        "orchestrator",
        "order_approved",
        "order",
        order_id,
        {"total_value": order["total_value"], "item_count": len(order.get("items", []))},
    )
    return order


async def reject_order(order_id: str) -> dict:
    update_order_status(order_id, "rejected", "wholesaler")
    order = get_order_by_id(order_id)
    if not order:
        return {"error": "Order not found"}

    log_agent_action("orchestrator", "order_rejected", "order", order_id, {"total_value": order["total_value"]})
    return order


async def substitute_item(order_id: str, item_id: str, substitute_product_id: str) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        return {"error": "Order not found"}

    from app.crud import get_product_by_id
    substitute = get_product_by_id(substitute_product_id)
    if not substitute:
        return {"error": "Substitute product not found"}

    items = order.get("items", [])
    original_name = ""
    new_items = []
    for item in items:
        if item["id"] == item_id:
            original_name = item.get("product_name", "the item")
            new_items.append({
                "product_id": substitute_product_id,
                "quantity": item["quantity"],
                "unit_price": substitute["price_default"],
                "matched_confidence": 1.0,
                "original_text": item.get("original_text", ""),
                "substitution_for": item["product_id"],
            })
        else:
            new_items.append({
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "matched_confidence": item.get("matched_confidence", 1.0),
                "original_text": item.get("original_text", ""),
            })

    update_order_items(order_id, new_items)

    phone = order.get("customer_whatsapp", "")
    if phone:
        msg = (
            f"{original_name} is currently unavailable. "
            f"We suggest {substitute['name']} instead at EUR {substitute['price_default']:.2f}/{substitute['unit']}. "
            f"Reply 'OK' to confirm or let us know your preference."
        )
        await send_whatsapp_message(phone, msg)
        save_conversation(order["customer_id"], "outbound", msg, "substitution_suggestion")

    log_agent_action(
        "orchestrator",
        "item_substituted",
        "order",
        order_id,
        {"original_item": item_id, "substitute": substitute_product_id},
    )
    return get_order_by_id(order_id)  # type: ignore[return-value]
