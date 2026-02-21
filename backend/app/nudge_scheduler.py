import logging
from datetime import datetime, timedelta

from app.crud import (
    get_overdue_customers,
    get_customer_context,
    get_customer_order_history,
    save_conversation,
    log_agent_action,
    create_alert,
    update_order_pattern,
)
from app.whatsapp import send_whatsapp_message

logger = logging.getLogger(__name__)


def _generate_nudge_message(customer_name: str, basket_items: list[dict]) -> str:
    lines = [f"Hi {customer_name}, your usual order is still open. Shall we place it?"]
    for item in basket_items[:8]:
        lines.append(f"  - {item['usual_quantity']}{item['unit']} {item['name']}")
    lines.append("Just reply 'Yes' to confirm or send any changes.")
    return "\n".join(lines)


async def run_nudge_scan() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    overdue = get_overdue_customers(today)

    nudges_sent = 0
    alerts_created = 0

    for customer in overdue:
        customer_id = customer["customer_id"]
        customer_name = customer["name"]
        phone = customer["contact_whatsapp"]
        health_score = customer.get("health_score", 1.0)

        earliest_expected = customer.get("earliest_expected", today)
        try:
            expected_dt = datetime.strptime(earliest_expected, "%Y-%m-%d")
            days_overdue = (datetime.now() - expected_dt).days
        except ValueError:
            days_overdue = 1

        context = get_customer_context(customer_id)
        basket = context.get("typical_basket", []) if context else []

        if days_overdue >= 7 or health_score < 0.8:
            history = get_customer_order_history(customer_id, 8)
            recent_values = [o["total_value"] for o in history[:4]] if history else []
            older_values = [o["total_value"] for o in history[4:8]] if len(history) > 4 else []

            avg_recent = sum(recent_values) / len(recent_values) if recent_values else 0
            avg_older = sum(older_values) / len(older_values) if older_values else avg_recent

            decline_pct = ((avg_older - avg_recent) / avg_older * 100) if avg_older > 0 else 0

            detail = (
                f"{customer_name} is {days_overdue} days overdue. "
                f"Health score: {health_score:.2f}. "
            )
            if decline_pct > 10:
                detail += f"Order value declining by {decline_pct:.0f}% over recent orders."

            create_alert("churn_risk", customer_id, detail)
            alerts_created += 1

            log_agent_action(
                "nudge_scheduler",
                "churn_alert_created",
                "customer",
                customer_id,
                {"days_overdue": days_overdue, "health_score": health_score, "decline_pct": round(decline_pct, 1)},
            )

        if basket and days_overdue < 14:
            message = _generate_nudge_message(customer_name, basket)
            await send_whatsapp_message(phone, message)
            save_conversation(customer_id, "outbound", message, "reorder_nudge")
            nudges_sent += 1

            log_agent_action(
                "nudge_scheduler",
                "nudge_sent",
                "customer",
                customer_id,
                {"days_overdue": days_overdue, "basket_items": len(basket)},
            )

    return {
        "scan_date": today,
        "overdue_customers": len(overdue),
        "nudges_sent": nudges_sent,
        "alerts_created": alerts_created,
    }


def update_patterns_after_order(customer_id: str, order_items: list[dict]) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    for item in order_items:
        product_id = item.get("product_id", "")
        quantity = item.get("quantity", 0)
        if product_id and quantity > 0:
            update_order_pattern(customer_id, product_id, today, 7.0, quantity)
