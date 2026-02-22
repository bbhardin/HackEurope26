SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    contact_phone TEXT UNIQUE NOT NULL,
    contact_whatsapp TEXT UNIQUE NOT NULL,
    delivery_address TEXT NOT NULL,
    health_score REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sku TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    unit TEXT NOT NULL,
    unit_type TEXT NOT NULL DEFAULT 'continuous',
    price_default REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS customer_context (
    customer_id TEXT PRIMARY KEY REFERENCES customers(id),
    context_json TEXT NOT NULL,
    last_updated TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS customer_prices (
    customer_id TEXT NOT NULL REFERENCES customers(id),
    product_id TEXT NOT NULL REFERENCES products(id),
    price REAL NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    PRIMARY KEY (customer_id, product_id, valid_from)
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    raw_message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    total_value REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    confirmed_at TEXT,
    confirmed_by TEXT,
    fulfilled_at TEXT,
    flags_json TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id),
    product_id TEXT NOT NULL REFERENCES products(id),
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    matched_confidence REAL NOT NULL DEFAULT 1.0,
    original_text TEXT NOT NULL DEFAULT '',
    substitution_for TEXT
);

CREATE TABLE IF NOT EXISTS agent_actions (
    id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}',
    confidence REAL,
    human_reviewed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    direction TEXT NOT NULL,
    message_text TEXT NOT NULL,
    parsed_intent TEXT,
    source TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_patterns (
    customer_id TEXT NOT NULL REFERENCES customers(id),
    product_id TEXT NOT NULL REFERENCES products(id),
    avg_interval_days REAL NOT NULL,
    avg_quantity REAL NOT NULL,
    last_order_date TEXT NOT NULL,
    next_expected_date TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.8,
    PRIMARY KEY (customer_id, product_id)
);

CREATE TABLE IF NOT EXISTS customer_health_events (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    customer_id TEXT REFERENCES customers(id),
    detail TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def apply_schema(conn) -> None:  # type: ignore[no-untyped-def]
    conn.executescript(SCHEMA_SQL)
