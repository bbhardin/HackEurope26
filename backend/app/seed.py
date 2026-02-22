import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from app.config import DATABASE_PATH
from app.schema import apply_schema

CATEGORIES = {
    "meat": [
        ("Chicken Breast", "MEAT-001", "kg", 4.20),
        ("Pork Tenderloin", "MEAT-002", "kg", 6.50),
        ("Beef Sirloin", "MEAT-003", "kg", 12.80),
        ("Ground Beef", "MEAT-004", "kg", 5.90),
        ("Lamb Leg", "MEAT-005", "kg", 14.50),
        ("Turkey Breast", "MEAT-006", "kg", 5.10),
        ("Bacon Slices", "MEAT-007", "kg", 7.20),
        ("Pork Belly", "MEAT-008", "kg", 5.80),
        ("Veal Cutlet", "MEAT-009", "kg", 16.90),
        ("Duck Breast", "MEAT-010", "kg", 13.40),
        ("Chicken Wings", "MEAT-011", "kg", 3.40),
        ("Sausages Mixed", "MEAT-012", "kg", 4.80),
        ("Salami Sliced", "MEAT-013", "kg", 9.50),
        ("Ham Cooked", "MEAT-014", "kg", 8.20),
        ("Chorizo", "MEAT-015", "kg", 10.30),
    ],
    "dairy": [
        ("Emmentaler Cheese 500g", "DAIRY-001", "pc", 4.50),
        ("Gouda Cheese 500g", "DAIRY-002", "pc", 3.80),
        ("Mozzarella Fresh 250g", "DAIRY-003", "pc", 2.20),
        ("Parmesan Block 1kg", "DAIRY-004", "pc", 12.50),
        ("Butter Unsalted 250g", "DAIRY-005", "pc", 2.80),
        ("Heavy Cream 1L", "DAIRY-006", "L", 3.20),
        ("Whole Milk 1L", "DAIRY-007", "L", 1.10),
        ("Sour Cream 500g", "DAIRY-008", "pc", 2.40),
        ("Cream Cheese 200g", "DAIRY-009", "pc", 1.90),
        ("Yogurt Natural 1kg", "DAIRY-010", "pc", 2.60),
        ("Feta Cheese 400g", "DAIRY-011", "pc", 3.50),
        ("Brie Wheel 500g", "DAIRY-012", "pc", 5.20),
        ("Cheddar Block 500g", "DAIRY-013", "pc", 4.10),
        ("Ricotta 500g", "DAIRY-014", "pc", 3.30),
        ("Blue Cheese 300g", "DAIRY-015", "pc", 5.80),
    ],
    "produce": [
        ("Potatoes", "PROD-001", "kg", 1.10),
        ("Onions Yellow", "PROD-002", "kg", 0.90),
        ("Carrots", "PROD-003", "kg", 1.20),
        ("Tomatoes Vine", "PROD-004", "kg", 2.80),
        ("Italian Tomatoes", "PROD-005", "kg", 3.20),
        ("Bell Peppers Mixed", "PROD-006", "kg", 3.50),
        ("Lettuce Iceberg", "PROD-007", "pc", 1.40),
        ("Cucumber", "PROD-008", "pc", 0.80),
        ("Zucchini", "PROD-009", "kg", 2.10),
        ("Mushrooms Button", "PROD-010", "kg", 4.50),
        ("Garlic Bulbs", "PROD-011", "kg", 6.80),
        ("Lemons", "PROD-012", "kg", 2.50),
        ("Limes", "PROD-013", "kg", 3.10),
        ("Fresh Herbs Mixed", "PROD-014", "bunch", 1.80),
        ("Spinach Fresh", "PROD-015", "kg", 3.90),
        ("Broccoli", "PROD-016", "kg", 2.30),
        ("Cauliflower", "PROD-017", "pc", 2.00),
        ("Avocado", "PROD-018", "pc", 1.50),
        ("Sweet Potato", "PROD-019", "kg", 1.80),
        ("Celery", "PROD-020", "pc", 1.60),
    ],
    "beverages": [
        ("Sparkling Water 1.5L", "BEV-001", "bottle", 0.60),
        ("Still Water 1.5L", "BEV-002", "bottle", 0.50),
        ("Orange Juice 1L", "BEV-003", "bottle", 2.80),
        ("Apple Juice 1L", "BEV-004", "bottle", 2.40),
        ("Cola 1L", "BEV-005", "bottle", 1.20),
        ("Lemonade 1L", "BEV-006", "bottle", 1.30),
        ("Tonic Water 1L", "BEV-007", "bottle", 1.80),
        ("Espresso Beans 1kg", "BEV-008", "kg", 14.50),
        ("Black Tea 100 bags", "BEV-009", "box", 4.20),
        ("Green Tea 50 bags", "BEV-010", "box", 3.80),
        ("Hot Chocolate Mix 1kg", "BEV-011", "kg", 8.50),
        ("Beer Pilsner 500ml", "BEV-012", "bottle", 1.40),
        ("Beer Wheat 500ml", "BEV-013", "bottle", 1.60),
        ("White Wine House 750ml", "BEV-014", "bottle", 6.50),
        ("Red Wine House 750ml", "BEV-015", "bottle", 7.20),
        ("Prosecco 750ml", "BEV-016", "bottle", 5.80),
        ("Mineral Water 0.5L", "BEV-017", "bottle", 0.40),
        ("Energy Drink 250ml", "BEV-018", "can", 1.50),
        ("Cranberry Juice 1L", "BEV-019", "bottle", 3.20),
        ("Ginger Beer 330ml", "BEV-020", "bottle", 1.90),
    ],
    "dry_goods": [
        ("Olive Oil Extra Virgin 5L", "DRY-001", "L", 8.90),
        ("Sunflower Oil 5L", "DRY-002", "L", 3.80),
        ("Cooking Oil 20L", "DRY-003", "L", 2.50),
        ("Flour All Purpose 25kg", "DRY-004", "bag", 12.50),
        ("Pasta Spaghetti 5kg", "DRY-005", "bag", 4.80),
        ("Pasta Penne 5kg", "DRY-006", "bag", 4.80),
        ("Rice Basmati 5kg", "DRY-007", "bag", 7.20),
        ("Rice Arborio 5kg", "DRY-008", "bag", 8.50),
        ("Sugar White 1kg", "DRY-009", "kg", 1.20),
        ("Salt Fine 1kg", "DRY-010", "kg", 0.80),
        ("Black Pepper Ground 500g", "DRY-011", "pc", 6.50),
        ("Paprika Powder 500g", "DRY-012", "pc", 5.20),
        ("Canned Tomatoes 2.5kg", "DRY-013", "can", 3.40),
        ("Tomato Paste 1kg", "DRY-014", "pc", 2.80),
        ("Balsamic Vinegar 1L", "DRY-015", "bottle", 5.50),
        ("Soy Sauce 1L", "DRY-016", "bottle", 4.20),
        ("Mustard Dijon 1kg", "DRY-017", "pc", 3.90),
        ("Mayonnaise 5kg", "DRY-018", "bucket", 8.50),
        ("Ketchup 5kg", "DRY-019", "bucket", 7.20),
        ("Breadcrumbs 2kg", "DRY-020", "bag", 3.60),
        ("Honey 1kg", "DRY-021", "jar", 9.80),
        ("Vanilla Extract 250ml", "DRY-022", "bottle", 12.50),
        ("Baking Powder 500g", "DRY-023", "pc", 2.10),
        ("Coconut Milk 1L", "DRY-024", "can", 2.40),
        ("Chickpeas Canned 400g", "DRY-025", "can", 1.20),
    ],
    "frozen": [
        ("French Fries 2.5kg", "FRZ-001", "bag", 4.50),
        ("Fish Sticks 1kg", "FRZ-002", "box", 5.80),
        ("Frozen Peas 2.5kg", "FRZ-003", "bag", 3.20),
        ("Ice Cream Vanilla 5L", "FRZ-004", "tub", 12.50),
        ("Frozen Shrimp 1kg", "FRZ-005", "bag", 14.80),
        ("Pizza Dough Balls 10pc", "FRZ-006", "bag", 6.50),
        ("Frozen Berries Mix 1kg", "FRZ-007", "bag", 7.20),
        ("Frozen Spinach 2.5kg", "FRZ-008", "bag", 4.10),
        ("Frozen Corn 2.5kg", "FRZ-009", "bag", 3.50),
        ("Frozen Salmon Fillets 1kg", "FRZ-010", "bag", 16.90),
    ],
    "seafood": [
        ("Salmon Fillet Fresh", "SEA-001", "kg", 18.50),
        ("Cod Fillet Fresh", "SEA-002", "kg", 14.20),
        ("Tuna Steak Fresh", "SEA-003", "kg", 22.50),
        ("Prawns Large Fresh", "SEA-004", "kg", 19.80),
        ("Mussels Fresh 1kg", "SEA-005", "kg", 6.50),
        ("Squid Cleaned", "SEA-006", "kg", 11.20),
        ("Sea Bass Whole", "SEA-007", "kg", 15.80),
        ("Smoked Salmon 200g", "SEA-008", "pc", 5.90),
        ("Anchovies in Oil 200g", "SEA-009", "pc", 3.40),
        ("Crab Meat 250g", "SEA-010", "pc", 8.50),
    ],
    "bakery": [
        ("Bread White Loaf", "BAK-001", "pc", 2.20),
        ("Bread Sourdough Loaf", "BAK-002", "pc", 3.50),
        ("Bread Rolls 10pc", "BAK-003", "bag", 3.80),
        ("Ciabatta 4pc", "BAK-004", "bag", 4.20),
        ("Croissants 6pc", "BAK-005", "bag", 5.50),
        ("Tortilla Wraps 10pc", "BAK-006", "pack", 3.20),
        ("Pita Bread 10pc", "BAK-007", "pack", 2.80),
        ("Burger Buns 8pc", "BAK-008", "bag", 3.40),
        ("Baguette", "BAK-009", "pc", 1.80),
        ("Focaccia", "BAK-010", "pc", 4.50),
    ],
    "eggs": [
        ("Eggs Free Range 30pc", "EGG-001", "tray", 8.50),
        ("Eggs Free Range 10pc", "EGG-002", "box", 3.20),
        ("Quail Eggs 20pc", "EGG-003", "box", 5.80),
    ],
    "condiments": [
        ("Hot Sauce 500ml", "COND-001", "bottle", 4.50),
        ("Worcestershire Sauce 500ml", "COND-002", "bottle", 3.80),
        ("Tabasco 150ml", "COND-003", "bottle", 3.20),
        ("BBQ Sauce 1L", "COND-004", "bottle", 4.80),
        ("Pesto Green 500g", "COND-005", "jar", 5.50),
        ("Chili Flakes 250g", "COND-006", "pc", 4.20),
        ("Capers 200g", "COND-007", "jar", 3.90),
    ],
}

CUSTOMERS = [
    {
        "id": "cust-001",
        "name": "The Oak Restaurant",
        "type": "restaurant",
        "contact_phone": "+4917612345001",
        "contact_whatsapp": "+4917612345001",
        "delivery_address": "123 Oak Street, Cologne",
        "health_score": 0.95,
        "order_day": "Tuesday",
        "order_interval": 7,
        "basket": [
            ("MEAT-002", 15),
            ("PROD-002", 8),
            ("DRY-003", 20),
            ("PROD-001", 10),
            ("DRY-001", 5),
        ],
    },
    {
        "id": "cust-002",
        "name": "Chef Meyer's Kitchen",
        "type": "restaurant",
        "contact_phone": "+4917612345002",
        "contact_whatsapp": "+4917612345002",
        "delivery_address": "45 Market Lane, Cologne",
        "health_score": 0.92,
        "order_day": "Monday",
        "order_interval": 7,
        "basket": [
            ("MEAT-001", 20),
            ("PROD-001", 10),
            ("DRY-001", 5),
            ("DAIRY-001", 4),
            ("PROD-004", 5),
        ],
    },
    {
        "id": "cust-003",
        "name": "Grand Hotel Bonn",
        "type": "hotel",
        "contact_phone": "+4917612345003",
        "contact_whatsapp": "+4917612345003",
        "delivery_address": "1 Palace Avenue, Bonn",
        "health_score": 0.88,
        "order_day": "Monday",
        "order_interval": 3,
        "basket": [
            ("MEAT-001", 40),
            ("MEAT-003", 15),
            ("SEA-001", 10),
            ("DAIRY-006", 20),
            ("EGG-001", 5),
            ("BEV-001", 48),
            ("BAK-005", 10),
            ("PROD-001", 25),
            ("PROD-004", 10),
            ("DRY-001", 10),
        ],
    },
    {
        "id": "cust-004",
        "name": "Bella Italia Trattoria",
        "type": "restaurant",
        "contact_phone": "+4917612345004",
        "contact_whatsapp": "+4917612345004",
        "delivery_address": "78 Via Roma Street, Cologne",
        "health_score": 0.97,
        "order_day": "Wednesday",
        "order_interval": 7,
        "basket": [
            ("DRY-005", 3),
            ("DRY-006", 2),
            ("DAIRY-003", 10),
            ("DAIRY-004", 2),
            ("PROD-005", 8),
            ("DRY-001", 5),
            ("DRY-013", 5),
        ],
    },
    {
        "id": "cust-005",
        "name": "Rhine Catering Co.",
        "type": "caterer",
        "contact_phone": "+4917612345005",
        "contact_whatsapp": "+4917612345005",
        "delivery_address": "200 Industrial Park, Cologne",
        "health_score": 0.85,
        "order_day": "Monday",
        "order_interval": 7,
        "basket": [
            ("MEAT-001", 50),
            ("MEAT-004", 30),
            ("PROD-001", 40),
            ("PROD-002", 20),
            ("DRY-004", 2),
            ("DRY-003", 40),
            ("EGG-001", 10),
        ],
    },
    {
        "id": "cust-006",
        "name": "Campus Canteen North",
        "type": "canteen",
        "contact_phone": "+4917612345006",
        "contact_whatsapp": "+4917612345006",
        "delivery_address": "University Campus, Building D, Bonn",
        "health_score": 0.90,
        "order_day": "Friday",
        "order_interval": 7,
        "basket": [
            ("MEAT-001", 60),
            ("MEAT-004", 40),
            ("PROD-001", 50),
            ("DRY-005", 5),
            ("DRY-006", 5),
            ("BEV-001", 96),
            ("FRZ-001", 10),
        ],
    },
    {
        "id": "cust-007",
        "name": "Sunrise Bakery Cafe",
        "type": "restaurant",
        "contact_phone": "+4917612345007",
        "contact_whatsapp": "+4917612345007",
        "delivery_address": "33 Baker Street, Cologne",
        "health_score": 0.93,
        "order_day": "Tuesday",
        "order_interval": 3,
        "basket": [
            ("DRY-004", 3),
            ("DAIRY-005", 10),
            ("EGG-001", 4),
            ("DAIRY-007", 20),
            ("DRY-009", 5),
            ("DRY-022", 2),
        ],
    },
    {
        "id": "cust-008",
        "name": "Seaside Fish Bar",
        "type": "restaurant",
        "contact_phone": "+4917612345008",
        "contact_whatsapp": "+4917612345008",
        "delivery_address": "5 Harbor Road, Cologne",
        "health_score": 0.78,
        "order_day": "Monday",
        "order_interval": 7,
        "basket": [
            ("SEA-002", 12),
            ("SEA-004", 8),
            ("FRZ-001", 5),
            ("PROD-012", 3),
            ("DRY-002", 10),
        ],
    },
    {
        "id": "cust-009",
        "name": "The Burger Joint",
        "type": "restaurant",
        "contact_phone": "+4917612345009",
        "contact_whatsapp": "+4917612345009",
        "delivery_address": "12 Main Street, Cologne",
        "health_score": 0.91,
        "order_day": "Wednesday",
        "order_interval": 4,
        "basket": [
            ("MEAT-004", 25),
            ("DAIRY-013", 6),
            ("BAK-008", 10),
            ("PROD-007", 8),
            ("PROD-004", 5),
            ("COND-004", 3),
            ("DRY-019", 2),
        ],
    },
    {
        "id": "cust-010",
        "name": "Vineyard Restaurant",
        "type": "restaurant",
        "contact_phone": "+4917612345010",
        "contact_whatsapp": "+4917612345010",
        "delivery_address": "88 Wine Hill, Bonn",
        "health_score": 0.96,
        "order_day": "Thursday",
        "order_interval": 7,
        "basket": [
            ("BEV-014", 12),
            ("BEV-015", 12),
            ("BEV-016", 6),
            ("MEAT-003", 8),
            ("SEA-001", 5),
            ("DAIRY-012", 4),
            ("PROD-010", 3),
        ],
    },
    {
        "id": "cust-011",
        "name": "Quick Bites Deli",
        "type": "small_retail",
        "contact_phone": "+4917612345011",
        "contact_whatsapp": "+4917612345011",
        "delivery_address": "55 Station Road, Cologne",
        "health_score": 0.82,
        "order_day": "Monday",
        "order_interval": 7,
        "basket": [
            ("MEAT-014", 5),
            ("MEAT-013", 3),
            ("DAIRY-002", 6),
            ("BAK-001", 10),
            ("BAK-003", 5),
        ],
    },
    {
        "id": "cust-012",
        "name": "Green Garden Vegan",
        "type": "restaurant",
        "contact_phone": "+4917612345012",
        "contact_whatsapp": "+4917612345012",
        "delivery_address": "7 Park Lane, Cologne",
        "health_score": 0.89,
        "order_day": "Tuesday",
        "order_interval": 7,
        "basket": [
            ("PROD-018", 20),
            ("PROD-015", 8),
            ("PROD-010", 5),
            ("DRY-024", 10),
            ("DRY-025", 8),
            ("PROD-009", 6),
        ],
    },
    {
        "id": "cust-013",
        "name": "Steakhouse Prime",
        "type": "restaurant",
        "contact_phone": "+4917612345013",
        "contact_whatsapp": "+4917612345013",
        "delivery_address": "99 Grill Avenue, Bonn",
        "health_score": 0.94,
        "order_day": "Monday",
        "order_interval": 4,
        "basket": [
            ("MEAT-003", 20),
            ("MEAT-005", 10),
            ("PROD-001", 15),
            ("PROD-010", 5),
            ("BEV-015", 8),
            ("COND-001", 2),
        ],
    },
    {
        "id": "cust-014",
        "name": "Little Dragon Asian",
        "type": "restaurant",
        "contact_phone": "+4917612345014",
        "contact_whatsapp": "+4917612345014",
        "delivery_address": "21 East Street, Cologne",
        "health_score": 0.87,
        "order_day": "Wednesday",
        "order_interval": 7,
        "basket": [
            ("DRY-007", 4),
            ("DRY-016", 3),
            ("MEAT-001", 15),
            ("FRZ-005", 5),
            ("PROD-011", 2),
            ("PROD-003", 5),
        ],
    },
    {
        "id": "cust-real-001",
        "name": "Mantas",
        "type": "restaurant",
        "contact_phone": "+447460880940",
        "contact_whatsapp": "+447460880940",
        "delivery_address": "London, UK",
        "health_score": 1.0,
        "order_day": "Monday",
        "order_interval": 7,
        "basket": [
            ("MEAT-001", 10),
            ("PROD-001", 5),
            ("DRY-001", 3),
        ],
    },
    {
        "id": "cust-real-002",
        "name": "Ben",
        "type": "restaurant",
        "contact_phone": "+18128017698",
        "contact_whatsapp": "+18128017698",
        "delivery_address": "Bloomington, IN, USA",
        "health_score": 1.0,
        "order_day": "Wednesday",
        "order_interval": 7,
        "basket": [
            ("MEAT-001", 15),
            ("PROD-004", 5),
            ("DRY-005", 2),
        ],
    },
    {
        "id": "cust-015",
        "name": "Riverside Hotel",
        "type": "hotel",
        "contact_phone": "+4917612345015",
        "contact_whatsapp": "+4917612345015",
        "delivery_address": "300 Riverside Drive, Bonn",
        "health_score": 0.91,
        "order_day": "Monday",
        "order_interval": 3,
        "basket": [
            ("MEAT-001", 30),
            ("MEAT-003", 10),
            ("SEA-001", 8),
            ("EGG-001", 6),
            ("DAIRY-006", 15),
            ("BAK-005", 8),
            ("BEV-008", 3),
            ("PROD-001", 20),
        ],
    },
]

DAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

SAMPLE_ORDER_MESSAGES = [
    "Hi, I'd like to place my usual order please",
    "Hey, need the regular delivery for this week",
    "Same as last time please, thanks",
    "Hi there, can we get our weekly order in?",
    "Please send the usual, same quantities",
    "Order for this week: same items as always",
    "Morning! Time for our regular order",
    "Hi, we need a restock — the usual please",
    "Hey, putting in our weekly order",
    "Can you send our standard order please?",
]

CONFIRMATION_TEMPLATES = [
    "Order confirmed! Delivery scheduled as requested.",
    "Got it! Your order has been placed. Expect delivery as usual.",
    "All set! Order confirmed and on its way.",
    "Order received and confirmed. See you at delivery!",
    "Thanks! Order is confirmed. Delivery on schedule.",
]


def _uid() -> str:
    return str(uuid.uuid4())[:8]


def seed_products(conn: sqlite3.Connection) -> dict[str, str]:
    sku_to_id: dict[str, str] = {}
    for category, items in CATEGORIES.items():
        for name, sku, unit, price in items:
            pid = f"prod-{sku.lower()}"
            sku_to_id[sku] = pid
            unit_type = "continuous" if unit in ("kg", "L") else "discrete"
            conn.execute(
                "INSERT OR IGNORE INTO products (id, name, sku, category, unit, unit_type, price_default) VALUES (?,?,?,?,?,?,?)",
                (pid, name, sku, category, unit, unit_type, price),
            )
    return sku_to_id


def seed_customers(conn: sqlite3.Connection) -> None:
    for c in CUSTOMERS:
        conn.execute(
            "INSERT OR IGNORE INTO customers (id, name, type, contact_phone, contact_whatsapp, delivery_address, health_score) VALUES (?,?,?,?,?,?,?)",
            (c["id"], c["name"], c["type"], c["contact_phone"], c["contact_whatsapp"], c["delivery_address"], c["health_score"]),
        )


def seed_customer_context(conn: sqlite3.Connection, sku_to_id: dict[str, str]) -> None:
    for c in CUSTOMERS:
        basket = []
        for sku, qty in c["basket"]:
            row = conn.execute("SELECT name, unit, price_default FROM products WHERE sku = ?", (sku,)).fetchone()
            if row:
                basket.append({
                    "product_id": sku_to_id[sku],
                    "sku": sku,
                    "name": row["name"],
                    "usual_quantity": qty,
                    "unit": row["unit"],
                    "price": row["price_default"],
                })

        context = {
            "typical_basket": basket,
            "order_frequency": f"every {c['order_interval']} days",
            "preferred_order_day": c["order_day"],
            "delivery_preferences": f"Standard delivery to {c['delivery_address']}",
            "notes": f"Regular {c['type']} customer. Orders typically on {c['order_day']}s.",
        }
        conn.execute(
            "INSERT OR REPLACE INTO customer_context (customer_id, context_json, last_updated) VALUES (?,?,datetime('now'))",
            (c["id"], json.dumps(context)),
        )


def seed_order_history(conn: sqlite3.Connection, sku_to_id: dict[str, str]) -> None:
    import random
    random.seed(42)
    now = datetime.now()

    for c in CUSTOMERS:
        interval = c["order_interval"]
        target_day = DAY_MAP[c["order_day"]]
        start = now - timedelta(weeks=12)
        current = start
        while current.weekday() != target_day:
            current += timedelta(days=1)

        while current < now - timedelta(days=1):
            order_id = f"ord-{_uid()}"
            msg_idx = random.randint(0, len(SAMPLE_ORDER_MESSAGES) - 1)
            total = 0.0
            items_data = []
            for sku, base_qty in c["basket"]:
                variation = random.uniform(0.8, 1.2)
                pid = sku_to_id[sku]
                prod_row = conn.execute("SELECT price_default, unit_type FROM products WHERE id = ?", (pid,)).fetchone()
                if prod_row and prod_row["unit_type"] == "discrete":
                    qty = max(1, round(base_qty * variation))
                else:
                    qty = round(base_qty * variation, 1)
                row = prod_row
                price = row["price_default"] if row else 0.0
                line_total = qty * price
                total += line_total
                items_data.append((pid, qty, price, sku))

            order_time = current.replace(hour=random.randint(18, 23), minute=random.randint(0, 59))
            confirm_time = (current + timedelta(hours=random.randint(8, 14))).isoformat()

            fulfilled_time = (current + timedelta(hours=random.randint(14, 20))).isoformat()
            conn.execute(
                "INSERT INTO orders (id, customer_id, channel, raw_message, status, total_value, created_at, confirmed_at, confirmed_by, fulfilled_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (order_id, c["id"], "whatsapp", SAMPLE_ORDER_MESSAGES[msg_idx], "fulfilled", round(total, 2), order_time.isoformat(), confirm_time, "sales_team", fulfilled_time),
            )

            for pid, qty, price, sku in items_data:
                conn.execute(
                    "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, matched_confidence, original_text) VALUES (?,?,?,?,?,?,?)",
                    (_uid(), order_id, pid, qty, price, round(random.uniform(0.9, 1.0), 2), f"{qty} of {sku}"),
                )

            conv_id = _uid()
            conn.execute(
                "INSERT INTO conversations (id, customer_id, channel, direction, message_text, parsed_intent, source, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (conv_id, c["id"], "whatsapp", "inbound", SAMPLE_ORDER_MESSAGES[msg_idx], "place_order", "system", order_time.isoformat()),
            )
            conf_msg = random.choice(CONFIRMATION_TEMPLATES)
            conn.execute(
                "INSERT INTO conversations (id, customer_id, channel, direction, message_text, parsed_intent, source, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (_uid(), c["id"], "whatsapp", "outbound", conf_msg, None, "system", confirm_time),
            )

            current += timedelta(days=interval)


def seed_order_patterns(conn: sqlite3.Connection, sku_to_id: dict[str, str]) -> None:
    now = datetime.now()
    for c in CUSTOMERS:
        interval = c["order_interval"]
        target_day = DAY_MAP[c["order_day"]]

        last_order_row = conn.execute(
            "SELECT created_at FROM orders WHERE customer_id = ? ORDER BY created_at DESC LIMIT 1",
            (c["id"],),
        ).fetchone()
        last_date = last_order_row["created_at"][:10] if last_order_row else now.strftime("%Y-%m-%d")
        last_dt = datetime.strptime(last_date, "%Y-%m-%d")
        next_expected = last_dt + timedelta(days=interval)

        for sku, qty in c["basket"]:
            pid = sku_to_id[sku]
            conn.execute(
                "INSERT OR REPLACE INTO order_patterns (customer_id, product_id, avg_interval_days, avg_quantity, last_order_date, next_expected_date, confidence) VALUES (?,?,?,?,?,?,?)",
                (c["id"], pid, interval, qty, last_date, next_expected.strftime("%Y-%m-%d"), 0.85),
            )


def seed_all() -> None:
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    apply_schema(conn)
    sku_to_id = seed_products(conn)
    seed_customers(conn)
    seed_customer_context(conn, sku_to_id)
    seed_order_history(conn, sku_to_id)
    seed_order_patterns(conn, sku_to_id)

    conn.commit()

    product_count = conn.execute("SELECT COUNT(*) as c FROM products").fetchone()["c"]
    customer_count = conn.execute("SELECT COUNT(*) as c FROM customers").fetchone()["c"]
    order_count = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
    conv_count = conn.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
    pattern_count = conn.execute("SELECT COUNT(*) as c FROM order_patterns").fetchone()["c"]

    print(f"Seeded: {product_count} products, {customer_count} customers, {order_count} orders, {conv_count} conversations, {pattern_count} order patterns")
    conn.close()


if __name__ == "__main__":
    seed_all()
