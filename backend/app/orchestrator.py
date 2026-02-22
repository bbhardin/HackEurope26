import logging

from app.crud import (
    create_order,
    get_customer_order_history,
    get_customer_context,
    save_conversation,
    log_agent_action,
    create_alert,
    create_health_event,
    update_order_status,
    update_order_items,
    get_order_by_id,
    get_orders_by_status,
    get_product_by_id,
    get_customer_by_id,
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
    low_confidence_items = []
    for item in items:
        confidence = item.get("matched_confidence", 0.9)
        order_items.append({
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "unit_price": item["unit_price"],
            "matched_confidence": confidence,
            "original_text": item.get("original_text", ""),
        })
        if confidence < 0.7:
            low_confidence_items.append(item)

    flags = list(anomalies) if anomalies else []
    notes = agent_output.get("notes", "")
    if notes:
        flags.append(f"Agent note: {notes}")

    has_anomalies = len([f for f in flags if not f.startswith("Agent note:")]) > 0
    has_low_confidence = len(low_confidence_items) > 0

    if has_low_confidence:
        status = "needs_clarification"
    elif has_anomalies:
        status = "flagged"
    else:
        status = "pending_confirmation"

    order = create_order(
        customer_id=customer["id"],
        raw_message=raw_message,
        items=order_items,
        status=status,
        flags=flags if flags else None,
    )

    if has_anomalies:
        for anomaly in anomalies:
            create_alert("anomaly", customer["id"], f"Order {order['id']}: {anomaly}")

    if notes:
        create_alert("agent_note", customer["id"], f"Order {order['id']}: {notes}")

    if has_low_confidence:
        await _send_clarification_message(customer, order, low_confidence_items)

    log_agent_action(
        "orchestrator",
        "order_created",
        "order",
        order["id"],
        {
            "intent": agent_output.get("intent"),
            "item_count": len(items),
            "total_value": order["total_value"],
            "flags": flags,
            "status": status,
        },
        agent_output.get("confidence"),
    )


async def _send_clarification_message(customer: dict, order: dict, low_confidence_items: list[dict]) -> None:
    lines = ["We received your order but need to confirm a few items:"]
    for item in low_confidence_items:
        original = item.get("original_text", "unknown item")
        matched = item.get("product_name", "")
        confidence = item.get("matched_confidence", 0)
        lines.append(f'  - You mentioned "{original}" — did you mean {matched}? (confidence: {confidence:.0%})')
    lines.append("Please reply to confirm or correct these items.")
    msg = "\n".join(lines)

    await send_whatsapp_message(customer["contact_whatsapp"], msg)
    save_conversation(customer["id"], "outbound", msg, "clarification_request")


async def _handle_modify_intent(customer: dict, agent_output: dict, raw_message: str) -> None:
    pending = get_orders_by_status("pending_confirmation")
    customer_pending = [o for o in pending if o["customer_id"] == customer["id"]]

    if not customer_pending:
        flagged = get_orders_by_status("flagged")
        customer_pending = [o for o in flagged if o["customer_id"] == customer["id"]]

    if not customer_pending:
        clarification = get_orders_by_status("needs_clarification")
        customer_pending = [o for o in clarification if o["customer_id"] == customer["id"]]

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


def _format_order_items(order: dict) -> list[str]:
    lines = []
    for item in order.get("items", []):
        name = item.get("product_name", item.get("product_id", "Unknown"))
        qty = item["quantity"]
        unit = item.get("unit", "")
        unit_type = item.get("unit_type", "continuous")
        price = item["unit_price"]
        line_total = qty * price
        qty_str = f"{int(qty)}" if unit_type == "discrete" else f"{qty}"
        lines.append(f"  - {qty_str}{unit} {name} (EUR {price:.2f}/{unit}) — EUR {line_total:.2f}")
    return lines


def generate_confirmation_message(order: dict) -> str:
    customer_name = order.get("customer_name", "Customer")
    lines = [f"Order received, {customer_name}:"]
    lines.extend(_format_order_items(order))
    lines.append(f"Total: EUR {order['total_value']:.2f}")
    lines.append("We'll notify you when it's dispatched.")
    return "\n".join(lines)


def generate_fulfilment_message(order: dict) -> str:
    customer_name = order.get("customer_name", "Customer")
    lines = [f"Your order has been dispatched, {customer_name}:"]
    lines.extend(_format_order_items(order))
    lines.append(f"Total: EUR {order['total_value']:.2f}")
    lines.append("Expected delivery: Next business day before 10:00")
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

    create_health_event(order["customer_id"], "returned_to_normal", "info", "Order confirmed")

    log_agent_action(
        "orchestrator",
        "order_approved",
        "order",
        order_id,
        {"total_value": order["total_value"], "item_count": len(order.get("items", []))},
    )
    return order


async def fulfil_order(order_id: str, custom_message: str = "") -> dict:
    update_order_status(order_id, "fulfilled", "wholesaler")
    order = get_order_by_id(order_id)
    if not order:
        return {"error": "Order not found"}

    message = custom_message if custom_message else generate_fulfilment_message(order)
    phone = order.get("customer_whatsapp", "")
    if phone:
        await send_whatsapp_message(phone, message)
        save_conversation(order["customer_id"], "outbound", message, "order_fulfilled")

    log_agent_action(
        "orchestrator",
        "order_fulfilled",
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

    create_health_event(order["customer_id"], "order_anomaly", "warning", "Order rejected by wholesaler")

    log_agent_action("orchestrator", "order_rejected", "order", order_id, {"total_value": order["total_value"]})
    return order


async def substitute_item(order_id: str, item_id: str, substitute_product_id: str) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        return {"error": "Order not found"}

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


async def send_manual_message(customer_id: str, message_text: str, order_id: str = "") -> dict:
    customer = get_customer_by_id(customer_id)
    if not customer:
        return {"status": "error", "error": "Customer not found", "detected_changes": []}

    await send_whatsapp_message(customer["contact_whatsapp"], message_text)
    save_conversation(customer_id, "outbound", message_text, "manual_message", "whatsapp", "manual")

    log_agent_action(
        "wholesaler",
        "manual_message",
        "customer",
        customer_id,
        {"message_preview": message_text[:200], "order_id": order_id},
    )

    detected_changes: list[dict] = []
    try:
        from app.customer_agent import analyse_outbound_message
        detected_changes = await analyse_outbound_message(customer_id, message_text)
    except Exception as e:
        logger.warning("Outbound analysis failed: %s", e)

    return {"status": "sent", "detected_changes": detected_changes}


async def send_clarification(order_id: str, message_text: str) -> dict:
    order = get_order_by_id(order_id)
    if not order:
        return {"error": "Order not found"}

    phone = order.get("customer_whatsapp", "")
    if phone:
        await send_whatsapp_message(phone, message_text)
        save_conversation(order["customer_id"], "outbound", message_text, "clarification_request", "whatsapp", "manual")

    log_agent_action("orchestrator", "clarification_sent", "order", order_id, {"message_preview": message_text[:200]})
    return {"status": "sent"}
