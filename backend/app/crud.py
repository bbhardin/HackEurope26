import json
import math
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db

DISCRETE_UNITS = {"pc", "bottle", "bag", "box", "tray", "can", "jar", "bunch", "tub", "pack", "bucket"}


def _uid() -> str:
    return str(uuid.uuid4())[:8]


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


def create_customer(name: str, phone: str, customer_type: str = "unknown", address: str = "Not provided") -> dict:
    customer_id = f"cust-{_uid()}"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO customers (id, name, type, contact_phone, contact_whatsapp, delivery_address, health_score, created_at) VALUES (?,?,?,?,?,?,1.0,?)",
            (customer_id, name, customer_type, phone, phone, address, datetime.now().isoformat()),
        )
        conn.execute(
            "INSERT INTO customer_context (customer_id, context_json, last_updated) VALUES (?,?,datetime('now'))",
            (customer_id, json.dumps({"typical_basket": [], "order_frequency": "unknown", "preferred_order_day": "unknown", "delivery_preferences": address, "notes": "New customer — profile auto-created"})),
        )
    return get_customer_by_id(customer_id)  # type: ignore[return-value]


def get_customer_by_phone(phone: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM customers WHERE contact_phone = ? OR contact_whatsapp = ?",
            (phone, phone),
        ).fetchone()
        return _row_to_dict(row) if row else None


def get_customer_by_id(customer_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
        return _row_to_dict(row) if row else None


def get_all_customers() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT c.*,
                      (SELECT he.detail FROM customer_health_events he
                       WHERE he.customer_id = c.id ORDER BY he.created_at DESC LIMIT 1) as latest_health_event,
                      (SELECT he.severity FROM customer_health_events he
                       WHERE he.customer_id = c.id ORDER BY he.created_at DESC LIMIT 1) as latest_health_severity,
                      (SELECT he.created_at FROM customer_health_events he
                       WHERE he.customer_id = c.id ORDER BY he.created_at DESC LIMIT 1) as latest_health_date,
                      (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id AND o.status = 'pending_confirmation') as pending_order_count,
                      (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id AND o.status = 'confirmed') as confirmed_order_count,
                      (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id AND o.status = 'fulfilled') as fulfilled_order_count
               FROM customers c ORDER BY c.name"""
        ).fetchall()
        return _rows_to_dicts(rows)


def get_customer_context(customer_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT context_json FROM customer_context WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
        if row:
            return json.loads(row["context_json"])
        return None


def get_products_by_query(query: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE name LIKE ? OR sku LIKE ? OR category LIKE ? LIMIT 20",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
        return _rows_to_dicts(rows)


def get_product_by_id(product_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return _row_to_dict(row) if row else None


def get_all_products() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY category, name").fetchall()
        return _rows_to_dicts(rows)


def create_product(name: str, sku: str, category: str, unit: str, unit_type: str, price_default: float) -> dict:
    product_id = f"prod-{_uid()}"
    with get_db() as conn:
        conn.execute(
            "INSERT INTO products (id, name, sku, category, unit, unit_type, price_default) VALUES (?,?,?,?,?,?,?)",
            (product_id, name, sku, category, unit, unit_type, price_default),
        )
    return get_product_by_id(product_id)  # type: ignore[return-value]


def update_product(product_id: str, name: str, price_default: float) -> bool:
    with get_db() as conn:
        conn.execute(
            "UPDATE products SET name = ?, price_default = ? WHERE id = ?",
            (name, price_default, product_id),
        )
        return conn.total_changes > 0


def delete_product(product_id: str) -> bool:
    with get_db() as conn:
        has_orders = conn.execute(
            "SELECT COUNT(*) as c FROM order_items WHERE product_id = ?", (product_id,)
        ).fetchone()
        if has_orders and has_orders["c"] > 0:
            return False
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return conn.total_changes > 0


def search_products(query: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, sku, category, unit, unit_type, price_default FROM products WHERE name LIKE ? OR sku LIKE ? LIMIT 20",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
        return _rows_to_dicts(rows)


def validate_quantity(product_id: str, quantity: float) -> float:
    product = get_product_by_id(product_id)
    if product and product.get("unit_type") == "discrete":
        return float(math.ceil(quantity))
    return quantity


def get_customer_order_history(customer_id: str, limit: int = 20) -> list[dict]:
    with get_db() as conn:
        orders = conn.execute(
            "SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?",
            (customer_id, limit),
        ).fetchall()
        result = []
        for order in orders:
            order_dict = _row_to_dict(order)
            items = conn.execute(
                """SELECT oi.*, p.name as product_name, p.sku, p.unit, p.unit_type
                   FROM order_items oi
                   JOIN products p ON oi.product_id = p.id
                   WHERE oi.order_id = ?""",
                (order_dict["id"],),
            ).fetchall()
            order_dict["items"] = _rows_to_dicts(items)
            if order_dict.get("flags_json"):
                order_dict["flags"] = json.loads(order_dict["flags_json"])
            else:
                order_dict["flags"] = []
            result.append(order_dict)
        return result


def create_order(
    customer_id: str,
    raw_message: str,
    items: list[dict],
    status: str = "pending_confirmation",
    channel: str = "whatsapp",
    flags: Optional[list[str]] = None,
) -> dict:
    order_id = f"ord-{_uid()}"
    validated_items = []
    for item in items:
        qty = validate_quantity(item["product_id"], item["quantity"])
        validated_items.append({**item, "quantity": qty})

    total_value = sum(item["quantity"] * item["unit_price"] for item in validated_items)
    flags_json = json.dumps(flags) if flags else None

    with get_db() as conn:
        conn.execute(
            "INSERT INTO orders (id, customer_id, channel, raw_message, status, total_value, flags_json, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (order_id, customer_id, channel, raw_message, status, round(total_value, 2), flags_json, datetime.now().isoformat()),
        )
        for item in validated_items:
            conn.execute(
                "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, matched_confidence, original_text) VALUES (?,?,?,?,?,?,?)",
                (
                    _uid(),
                    order_id,
                    item["product_id"],
                    item["quantity"],
                    item["unit_price"],
                    item.get("matched_confidence", 1.0),
                    item.get("original_text", ""),
                ),
            )
    return get_order_by_id(order_id)  # type: ignore[return-value]


def get_order_by_id(order_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            return None
        order_dict = _row_to_dict(row)
        items = conn.execute(
            """SELECT oi.*, p.name as product_name, p.sku, p.unit, p.unit_type, p.category
               FROM order_items oi
               JOIN products p ON oi.product_id = p.id
               WHERE oi.order_id = ?""",
            (order_id,),
        ).fetchall()
        order_dict["items"] = _rows_to_dicts(items)
        if order_dict.get("flags_json"):
            order_dict["flags"] = json.loads(order_dict["flags_json"])
        else:
            order_dict["flags"] = []
        customer = conn.execute("SELECT name, contact_whatsapp FROM customers WHERE id = ?", (order_dict["customer_id"],)).fetchone()
        if customer:
            order_dict["customer_name"] = customer["name"]
            order_dict["customer_whatsapp"] = customer["contact_whatsapp"]
        return order_dict


def get_orders_by_status(status: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
        result = []
        for row in rows:
            order_dict = _row_to_dict(row)
            items = conn.execute(
                """SELECT oi.*, p.name as product_name, p.sku, p.unit, p.unit_type
                   FROM order_items oi
                   JOIN products p ON oi.product_id = p.id
                   WHERE oi.order_id = ?""",
                (order_dict["id"],),
            ).fetchall()
            order_dict["items"] = _rows_to_dicts(items)
            if order_dict.get("flags_json"):
                order_dict["flags"] = json.loads(order_dict["flags_json"])
            else:
                order_dict["flags"] = []
            customer = conn.execute("SELECT name FROM customers WHERE id = ?", (order_dict["customer_id"],)).fetchone()
            if customer:
                order_dict["customer_name"] = customer["name"]
            result.append(order_dict)
        return result


def get_all_orders(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for row in rows:
            order_dict = _row_to_dict(row)
            items = conn.execute(
                """SELECT oi.*, p.name as product_name, p.sku, p.unit, p.unit_type
                   FROM order_items oi
                   JOIN products p ON oi.product_id = p.id
                   WHERE oi.order_id = ?""",
                (order_dict["id"],),
            ).fetchall()
            order_dict["items"] = _rows_to_dicts(items)
            if order_dict.get("flags_json"):
                order_dict["flags"] = json.loads(order_dict["flags_json"])
            else:
                order_dict["flags"] = []
            customer = conn.execute("SELECT name FROM customers WHERE id = ?", (order_dict["customer_id"],)).fetchone()
            if customer:
                order_dict["customer_name"] = customer["name"]
            result.append(order_dict)
        return result


def update_order_status(order_id: str, status: str, confirmed_by: str = "system") -> bool:
    with get_db() as conn:
        confirmed_at = datetime.now().isoformat() if status == "confirmed" else None
        fulfilled_at = datetime.now().isoformat() if status == "fulfilled" else None
        conn.execute(
            """UPDATE orders SET status = ?,
               confirmed_at = COALESCE(?, confirmed_at),
               confirmed_by = COALESCE(?, confirmed_by),
               fulfilled_at = COALESCE(?, fulfilled_at)
               WHERE id = ?""",
            (status, confirmed_at, confirmed_by if status == "confirmed" else None, fulfilled_at, order_id),
        )
        return conn.total_changes > 0


def update_order_items(order_id: str, items: list[dict]) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        total_value = 0.0
        for item in items:
            qty = validate_quantity(item["product_id"], item["quantity"])
            line = qty * item["unit_price"]
            total_value += line
            conn.execute(
                "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, matched_confidence, original_text, substitution_for) VALUES (?,?,?,?,?,?,?,?)",
                (
                    _uid(),
                    order_id,
                    item["product_id"],
                    qty,
                    item["unit_price"],
                    item.get("matched_confidence", 1.0),
                    item.get("original_text", ""),
                    item.get("substitution_for"),
                ),
            )
        conn.execute("UPDATE orders SET total_value = ?, status = 'pending_confirmation' WHERE id = ?", (round(total_value, 2), order_id))
        return True


def log_agent_action(
    agent_type: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict,
    confidence: Optional[float] = None,
) -> str:
    action_id = _uid()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO agent_actions (id, agent_type, action, entity_type, entity_id, details_json, confidence, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (action_id, agent_type, action, entity_type, entity_id, json.dumps(details), confidence, datetime.now().isoformat()),
        )
    return action_id


def get_agent_actions(limit: int = 50, agent_type: Optional[str] = None) -> list[dict]:
    with get_db() as conn:
        base_query = """
            SELECT aa.*,
                CASE
                    WHEN aa.entity_type = 'customer' THEN (SELECT name FROM customers WHERE id = aa.entity_id)
                    WHEN aa.entity_type = 'order' THEN (SELECT c.name FROM orders o JOIN customers c ON o.customer_id = c.id WHERE o.id = aa.entity_id)
                    ELSE NULL
                END as customer_name,
                CASE
                    WHEN aa.entity_type = 'customer' THEN (SELECT id FROM customers WHERE id = aa.entity_id)
                    WHEN aa.entity_type = 'order' THEN (SELECT customer_id FROM orders WHERE id = aa.entity_id)
                    ELSE NULL
                END as resolved_customer_id,
                CASE
                    WHEN aa.entity_type = 'order' THEN aa.entity_id
                    ELSE NULL
                END as related_order_id
            FROM agent_actions aa
        """
        if agent_type:
            rows = conn.execute(
                base_query + " WHERE aa.agent_type = ? ORDER BY aa.created_at DESC LIMIT ?",
                (agent_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                base_query + " ORDER BY aa.created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return _rows_to_dicts(rows)


def save_conversation(
    customer_id: str,
    direction: str,
    message_text: str,
    parsed_intent: Optional[str] = None,
    channel: str = "whatsapp",
    source: str = "system",
) -> str:
    conv_id = _uid()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, customer_id, channel, direction, message_text, parsed_intent, source, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (conv_id, customer_id, channel, direction, message_text, parsed_intent, source, datetime.now().isoformat()),
        )
    return conv_id


def get_conversations(customer_id: str, limit: int = 20) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?",
            (customer_id, limit),
        ).fetchall()
        return _rows_to_dicts(rows)


def get_order_patterns(customer_id: Optional[str] = None) -> list[dict]:
    with get_db() as conn:
        if customer_id:
            rows = conn.execute(
                """SELECT op.*, p.name as product_name, c.name as customer_name
                   FROM order_patterns op
                   JOIN products p ON op.product_id = p.id
                   JOIN customers c ON op.customer_id = c.id
                   WHERE op.customer_id = ?""",
                (customer_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT op.*, p.name as product_name, c.name as customer_name
                   FROM order_patterns op
                   JOIN products p ON op.product_id = p.id
                   JOIN customers c ON op.customer_id = c.id""",
            ).fetchall()
        return _rows_to_dicts(rows)


def get_overdue_customers(current_date: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT DISTINCT op.customer_id, c.name, c.contact_whatsapp, c.health_score,
                      MIN(op.next_expected_date) as earliest_expected
               FROM order_patterns op
               JOIN customers c ON op.customer_id = c.id
               WHERE op.next_expected_date < ?
               AND NOT EXISTS (
                   SELECT 1 FROM orders o
                   WHERE o.customer_id = op.customer_id
                   AND o.status IN ('received','parsed','pending_confirmation','confirmed','fulfilled')
                   AND o.created_at >= op.next_expected_date
               )
               GROUP BY op.customer_id""",
            (current_date,),
        ).fetchall()
        return _rows_to_dicts(rows)


def create_alert(alert_type: str, customer_id: Optional[str], detail: str) -> str:
    alert_id = _uid()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO alerts (id, type, customer_id, detail, created_at) VALUES (?,?,?,?,?)",
            (alert_id, alert_type, customer_id, detail, datetime.now().isoformat()),
        )
    return alert_id


def get_alerts(acknowledged: bool = False, limit: int = 50) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.*, c.name as customer_name
               FROM alerts a
               LEFT JOIN customers c ON a.customer_id = c.id
               WHERE a.acknowledged = ?
               ORDER BY a.created_at DESC LIMIT ?""",
            (1 if acknowledged else 0, limit),
        ).fetchall()
        return _rows_to_dicts(rows)


def acknowledge_alert(alert_id: str) -> bool:
    with get_db() as conn:
        conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
        return conn.total_changes > 0


def create_nudge_suggestion(customer_id: str, suggested_message: str, reason: str) -> str:
    nudge_id = _uid()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO nudge_suggestions (id, customer_id, suggested_message, reason, created_at) VALUES (?,?,?,?,?)",
            (nudge_id, customer_id, suggested_message, reason, datetime.now().isoformat()),
        )
    return nudge_id


def get_nudge_suggestions(status: str = "pending") -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT ns.*, c.name as customer_name, c.contact_whatsapp
               FROM nudge_suggestions ns
               JOIN customers c ON ns.customer_id = c.id
               WHERE ns.status = ?
               ORDER BY ns.created_at DESC""",
            (status,),
        ).fetchall()
        return _rows_to_dicts(rows)


def get_nudge_suggestion_by_id(nudge_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            """SELECT ns.*, c.name as customer_name, c.contact_whatsapp
               FROM nudge_suggestions ns
               JOIN customers c ON ns.customer_id = c.id
               WHERE ns.id = ?""",
            (nudge_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None


def update_nudge_suggestion_status(nudge_id: str, status: str) -> bool:
    with get_db() as conn:
        conn.execute("UPDATE nudge_suggestions SET status = ? WHERE id = ?", (status, nudge_id))
        return conn.total_changes > 0


def get_customer_nudge_suggestions(customer_id: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM nudge_suggestions WHERE customer_id = ? AND status = 'pending' ORDER BY created_at DESC",
            (customer_id,),
        ).fetchall()
        return _rows_to_dicts(rows)


def get_orders_overview() -> dict:
    with get_db() as conn:
        pending = conn.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(total_value),0) as total FROM orders WHERE status = 'pending_confirmation'"
        ).fetchone()
        confirmed_today = conn.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(total_value),0) as total FROM orders WHERE status = 'confirmed' AND date(confirmed_at) = date('now')"
        ).fetchone()
        confirmed_all = conn.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(total_value),0) as total FROM orders WHERE status = 'confirmed'"
        ).fetchone()
        fulfilled_today = conn.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(total_value),0) as total FROM orders WHERE status = 'fulfilled' AND date(fulfilled_at) = date('now')"
        ).fetchone()
        fulfilled_all = conn.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(total_value),0) as total FROM orders WHERE status = 'fulfilled'"
        ).fetchone()
        rejected = conn.execute(
            "SELECT COUNT(*) as count FROM orders WHERE status = 'rejected'"
        ).fetchone()
        flagged = conn.execute(
            "SELECT COUNT(*) as count FROM orders WHERE status = 'flagged'"
        ).fetchone()
        return {
            "pending_count": pending["count"],
            "pending_value": round(pending["total"], 2),
            "confirmed_today_count": confirmed_today["count"],
            "confirmed_today_value": round(confirmed_today["total"], 2),
            "confirmed_all_count": confirmed_all["count"],
            "confirmed_all_value": round(confirmed_all["total"], 2),
            "fulfilled_today_count": fulfilled_today["count"],
            "fulfilled_today_value": round(fulfilled_today["total"], 2),
            "fulfilled_all_count": fulfilled_all["count"],
            "fulfilled_all_value": round(fulfilled_all["total"], 2),
            "rejected_count": rejected["count"],
            "flagged_count": flagged["count"],
        }


def update_order_pattern(customer_id: str, product_id: str, last_order_date: str, avg_interval: float, avg_quantity: float) -> None:
    next_expected = (datetime.strptime(last_order_date, "%Y-%m-%d") + timedelta(days=avg_interval)).strftime("%Y-%m-%d")
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO order_patterns
               (customer_id, product_id, avg_interval_days, avg_quantity, last_order_date, next_expected_date, confidence)
               VALUES (?,?,?,?,?,?,0.85)""",
            (customer_id, product_id, avg_interval, avg_quantity, last_order_date, next_expected),
        )


def get_aggregated_items(statuses: list[str]) -> list[dict]:
    with get_db() as conn:
        placeholders = ",".join("?" for _ in statuses)
        rows = conn.execute(
            f"""SELECT p.id as product_id, p.name as product_name, p.sku, p.category, p.unit, p.unit_type,
                       SUM(oi.quantity) as total_quantity, COUNT(DISTINCT o.id) as order_count
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE o.status IN ({placeholders})
                GROUP BY p.id
                ORDER BY p.category, p.name""",
            statuses,
        ).fetchall()
        return _rows_to_dicts(rows)


def create_health_event(customer_id: str, event_type: str, severity: str, detail: str) -> str:
    event_id = _uid()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO customer_health_events (id, customer_id, event_type, severity, detail, created_at) VALUES (?,?,?,?,?,?)",
            (event_id, customer_id, event_type, severity, detail, datetime.now().isoformat()),
        )
    recompute_health_score(customer_id)
    return event_id


def recompute_health_score(customer_id: str) -> float:
    cutoff = (datetime.now() - timedelta(days=28)).isoformat()
    with get_db() as conn:
        events = conn.execute(
            "SELECT severity FROM customer_health_events WHERE customer_id = ? AND created_at >= ?",
            (customer_id, cutoff),
        ).fetchall()
        score = 1.0
        for event in events:
            sev = event["severity"]
            if sev == "critical":
                score -= 0.15
            elif sev == "warning":
                score -= 0.05
            elif sev == "info":
                score += 0.02
        score = max(0.0, min(1.0, score))
        conn.execute("UPDATE customers SET health_score = ? WHERE id = ?", (round(score, 2), customer_id))
        return score


def get_health_events(customer_id: str, limit: int = 20) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM customer_health_events WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?",
            (customer_id, limit),
        ).fetchall()
        return _rows_to_dicts(rows)
