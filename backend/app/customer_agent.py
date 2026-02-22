import json
import logging
from typing import Optional

import anthropic

from app.config import ANTHROPIC_API_KEY
from app.crud import (
    get_customer_context,
    get_customer_order_history,
    get_products_by_query,
    get_all_products,
    get_order_patterns,
    get_orders_by_status,
)

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SYSTEM_PROMPT = """You are a Customer Agent for a food & beverage wholesaler. You process incoming WhatsApp messages from restaurant/hotel customers and classify their intent.

You have access to the customer's full context including their order history, typical basket, and preferences. Use this context to understand what they want.

You may receive text messages or images (e.g. handwritten order lists, photos of products or invoices). For images, analyse the visual content carefully to extract order information.

Your job:
1. Classify the intent of the message into one of:
   - place_order: Customer wants to place a new order
   - repeat_order: Customer wants to repeat a previous order (e.g., "the usual", "same as last time")
   - modify_order: Customer wants to change an existing pending order
   - remind_last_order: Customer asks about their last/recent order
   - general_inquiry: Any other question or conversation

2. For order intents (place_order, repeat_order), parse out the specific items:
   - Use the search_product_catalogue tool to match product names
   - Use customer context to resolve ambiguous references ("the usual olive oil" -> their typical olive oil from basket)
   - Extract quantities and units
   - Flag any anomalies (unusual quantities compared to history)

3. Return structured JSON output.

IMPORTANT RULES:
- Always use the customer's typical basket to resolve "the usual" or "same as last time"
- If a quantity seems unusual (>3x their average), flag it as an anomaly
- If you can't match a product, include it as unmatched with the original text
- Be generous in matching - "chicken" should match "Chicken Breast" if that's what the customer usually orders
- All communication is in English"""

TOOLS = [
    {
        "name": "search_product_catalogue",
        "description": "Search the product catalogue for items matching a query. Returns matching products with SKU, name, unit, and price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Product name or keyword to search for",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_customer_history",
        "description": "Get the customer's recent order history to understand patterns and typical orders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer ID",
                }
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "flag_anomaly",
        "description": "Flag an anomaly in the order for human review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Description of the anomaly",
                }
            },
            "required": ["reason"],
        },
    },
]


def _execute_tool(tool_name: str, tool_input: dict, customer_id: str) -> str:
    if tool_name == "search_product_catalogue":
        results = get_products_by_query(tool_input["query"])
        return json.dumps(results[:10])

    if tool_name == "get_customer_history":
        history = get_customer_order_history(customer_id, 5)
        simplified = []
        for order in history:
            simplified.append({
                "date": order["created_at"],
                "items": [
                    {"name": i["product_name"], "quantity": i["quantity"], "unit": i["unit"], "price": i["unit_price"]}
                    for i in order.get("items", [])
                ],
                "total": order["total_value"],
            })
        return json.dumps(simplified)

    if tool_name == "flag_anomaly":
        sigme("anomaly_flagged", True)
        return json.dumps({"flagged": True, "reason": tool_input["reason"]})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def _build_user_message(customer_id: str, text_content: str, message_type: str) -> str | list:
    context = get_customer_context(customer_id)
    patterns = get_order_patterns(customer_id)

    pending_orders = get_orders_by_status("pending_confirmation")
    customer_pending = [o for o in pending_orders if o["customer_id"] == customer_id]

    context_str = json.dumps(context, indent=2) if context else "No context available"
    patterns_str = json.dumps(patterns[:10], indent=2) if patterns else "No patterns available"
    pending_str = ""
    if customer_pending:
        pending_str = f"\n\nPENDING ORDERS FOR THIS CUSTOMER:\n{json.dumps(customer_pending, indent=2)}"

    prefix = f"""CUSTOMER CONTEXT:
{context_str}

ORDER PATTERNS:
{patterns_str}
{pending_str}

INCOMING MESSAGE (type: {message_type}):
"""

    suffix = """Please classify the intent and parse any order items. Return your analysis as a JSON object with this structure:
{
  "intent": "place_order|repeat_order|modify_order|remind_last_order|general_inquiry",
  "confidence": 0.0-1.0,
  "items": [
    {
      "product_id": "prod-xxx",
      "product_name": "Product Name",
      "quantity": 10,
      "unit": "kg",
      "unit_price": 4.20,
      "original_text": "what the customer said",
      "matched_confidence": 0.95
    }
  ],
  "anomalies": ["list of any flagged issues"],
  "response_text": "suggested response to send to customer",
  "notes": "any additional notes for the wholesaler"
}"""

    if message_type == "image" and text_content.startswith("[IMAGE:"):
        b64_data = text_content[7:-1]
        return [
            {"type": "text", "text": prefix},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64_data}},
            {"type": "text", "text": suffix},
        ]

    return prefix + text_content + "\n\n" + suffix

#@paid_tracing("testcustomer", external_product_id="test-external")
async def run_customer_agent(customer_id: str, text_content: str, message_type: str = "text") -> dict:
    #export PAID_API_KEY=
    if not client:
        print("HERE0")
        return _fallback_parse(customer_id, text_content)

    user_message = _build_user_message(customer_id, text_content, message_type)

    print("HERE3")
    #sigme("chat_completion")
    print("WOWZA")

    try:
        messages: list[dict] = [{"role": "user", "content": user_message}]

        print("-")
        # from paid import Paid
        # paid = Paid(token="6e918259-b19f-417b-a37d-338e9e4d5dbd")
        # paid.signals.create(customer_id="cus_5hgEqXKUroR", event="api_call")
        print("woah")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        print("--")
        # from paid import Paid
        # import paid
        # # paid api 2 6e918259-b19f-417b-a37d-338e9e4d5dbd

        #customer = paid.customers.create_customer(name="Acme Corp", email="acme@example.com")  
        # THIS ABOVE WORKS
        
        #paid.signals.create(customer_id="cus_5hg6bnudnWT", event="api_call")

        # paid.usage.record_bulk_v2(signals=[
        #     SignalV2(
        #         event_name="email_sent",
        #         product_id="YOUR_PRODUCT_ID",
        #         customer_id="YOUR_CUSTOMER_ID",
        #         data={"subject": "Follow-up"}
        #     )
        # ])
        print("thing")
    
        #signal("chat_completion")#, enable_cost_tracing=True)

        print("did a thing")
        

        # Record usage / trigger billing
        #paid.signals.create(customer_id="customer_123", event="api_call")
                # paid.usage.record(
        #     eventName="chat_completion",
        #     externalCustomerId="cus_5hg6bnudnWT",  # Your customer ID
        #     externalProductId="prod_5hg6X4dxa8F",  # Your product ID
        # )

        # Send a usage signal
        # paid.usage.usage_record_bulk_v_2(
        #     event_name="api_calls",  # Must match your product's configured event name
        #     external_customer_id="customer_123",  # Your customer ID
        #     external_product_id="product_456",  # Your product ID
        # )
        # paid.customers.create_customer(
        #     name="delete_me"
        # )

        #signal("chat_completion", True)

        print("HERE1")

        while response.stop_reason == "tool_use":
            tool_results = []
            assistant_content = response.content
            for block in assistant_content:
                if block.type == "tool_use":
                    result = _execute_tool(block.name, block.input, customer_id)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
            # signal("chat_completion", True)

        print("HERE")

        result_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                result_text += block.text

        try:
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(result_text[json_start:json_end])
                return parsed
        except json.JSONDecodeError:
            logger.error("Failed to parse agent JSON output: %s", result_text[:500])

        return {
            "intent": "general_inquiry",
            "confidence": 0.5,
            "items": [],
            "anomalies": [],
            "response_text": result_text,
            "notes": "Could not parse structured output",
        }

    except Exception as e:
        logger.error("Customer agent error: %s", e)
        return _fallback_parse(customer_id, text_content)


def _fallback_parse(customer_id: str, text_content: str) -> dict:
    text_lower = text_content.lower()

    if any(word in text_lower for word in ["usual", "same as", "repeat", "again", "last time", "regular"]):
        context = get_customer_context(customer_id)
        items = []
        if context and "typical_basket" in context:
            for item in context["typical_basket"]:
                items.append({
                    "product_id": item["product_id"],
                    "product_name": item["name"],
                    "quantity": item["usual_quantity"],
                    "unit": item["unit"],
                    "unit_price": item["price"],
                    "original_text": "the usual",
                    "matched_confidence": 0.9,
                })
        return {
            "intent": "repeat_order",
            "confidence": 0.7,
            "items": items,
            "anomalies": [],
            "response_text": "",
            "notes": "Fallback parser used — LLM unavailable",
        }

    if any(word in text_lower for word in ["last order", "previous order", "what did i order", "recent order"]):
        return {
            "intent": "remind_last_order",
            "confidence": 0.7,
            "items": [],
            "anomalies": [],
            "response_text": "",
            "notes": "Fallback parser used — LLM unavailable",
        }

    if any(word in text_lower for word in ["change", "modify", "update", "instead", "actually"]):
        return {
            "intent": "modify_order",
            "confidence": 0.6,
            "items": [],
            "anomalies": [],
            "response_text": "",
            "notes": "Fallback parser used — LLM unavailable. Modification details need manual review.",
        }

    if any(word in text_lower for word in ["need", "order", "send", "deliver", "want", "kg", "litre", "bottle", "yes"]):
        context = get_customer_context(customer_id)
        items = []
        if context and "typical_basket" in context:
            for item in context["typical_basket"]:
                if item["name"].lower() in text_lower or item["sku"].lower() in text_lower:
                    items.append({
                        "product_id": item["product_id"],
                        "product_name": item["name"],
                        "quantity": item["usual_quantity"],
                        "unit": item["unit"],
                        "unit_price": item["price"],
                        "original_text": text_content,
                        "matched_confidence": 0.7,
                    })

        if not items and context and "typical_basket" in context:
            for item in context["typical_basket"]:
                items.append({
                    "product_id": item["product_id"],
                    "product_name": item["name"],
                    "quantity": item["usual_quantity"],
                    "unit": item["unit"],
                    "unit_price": item["price"],
                    "original_text": text_content,
                    "matched_confidence": 0.5,
                })

        return {
            "intent": "place_order" if items else "general_inquiry",
            "confidence": 0.5,
            "items": items,
            "anomalies": ["Fallback parser — items may not be accurate"],
            "response_text": "",
            "notes": "Fallback parser used — LLM unavailable",
        }

    return {
        "intent": "general_inquiry",
        "confidence": 0.5,
        "items": [],
        "anomalies": [],
        "response_text": "Thank you for your message. A member of our team will get back to you shortly.",
        "notes": "Fallback parser used — LLM unavailable",
    }
