# Improvement Notes V1 — Response & Implementation Plan

This document addresses each of the 10 feedback items from `improvement_notes_v1.md`. For each item we diagnose the current behaviour, identify every affected file, and propose a concrete implementation approach.

---

## 1. Health Score Clarification for User

### Current behaviour
The health score is a static number (0.0–1.0) seeded per customer at database initialisation. It is **never recomputed** — no workflow updates it. The frontend displays it as a percentage with a three-tier colour label (Healthy / Watch / At Risk) but offers no explanation of *why* a customer has that score.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/schema.py` | Add a `customer_health_events` table to store individual health signals (missed orders, declining quantities, complaints, etc.) |
| `backend/app/crud.py` | Add functions to create health events and recompute the aggregate score |
| `backend/app/nudge_scheduler.py` | After detecting an overdue customer or declining order value, write a health event |
| `backend/app/orchestrator.py` | After order confirmation or rejection, write a health event |
| `frontend/src/app/customers/page.tsx` | Show the most recent health signal as a one-line reason underneath the score (e.g., "3 days overdue on usual Tuesday order") |
| `frontend/src/app/customers/[id]/page.tsx` | Add a "Health Timeline" section listing recent health events with severity badges |
| `frontend/src/lib/types.ts` | Add `HealthEvent` type |
| `frontend/src/lib/api.ts` | Add `getCustomerHealthEvents(id)` call |
| `backend/app/routers/customers.py` | Add `GET /api/customers/{id}/health-events` endpoint |

### Proposed approach
Replace the opaque 0–1 score with a **traffic-light system backed by observable events**:

1. **New table `customer_health_events`**: `(id, customer_id, event_type, severity, detail, created_at)`. Event types: `missed_order`, `declining_quantity`, `order_anomaly`, `late_payment`, `returned_to_normal`. Severity: `info | warning | critical`.

2. **Dynamic recomputation**: Each time a health event is written, recompute the customer's `health_score` as a weighted rolling average. For example: each `critical` event in the last 28 days subtracts 0.15, each `warning` subtracts 0.05, each `info` (positive) adds 0.02, clamped to [0, 1].

3. **Frontend**: On the customer list, display the latest event as a short reason line (e.g., "Missed Tuesday order · 3 days ago"). On the customer detail page, show a scrollable health timeline. Replace the raw percentage with the traffic-light badge prominently, and show the percentage only as secondary text.

### Complexity: Medium
The data model change is small. The main work is wiring up event creation in the nudge scheduler and orchestrator, and adding the timeline UI.

---

## 2. Fulfilment Differential from Order Accept

### Current behaviour
The order lifecycle has no `fulfilled` state. When the wholesaler clicks "Approve", the system simultaneously:
- Sets status to `confirmed`
- Sends the customer a confirmation message that includes "Delivery: Next business day before 10:00"

There is no way to mark an order as delivered/fulfilled after the fact. The confirmation message conflates "we accept your order" with "it's on its way".

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/schema.py` | Add `fulfilled` to the status enum comment; add `fulfilled_at` column to orders |
| `backend/app/crud.py` | Update `update_order_status` to handle `fulfilled`; update `get_orders_overview` to count fulfilled orders |
| `backend/app/orchestrator.py` | Split into two functions: `approve_order` (sends confirmation) and `fulfil_order` (sends delivery message). Rewrite `generate_confirmation_message` to only confirm receipt. Add `generate_fulfilment_message` for delivery notification. |
| `backend/app/routers/orders.py` | Add `POST /api/orders/{id}/fulfil` endpoint |
| `frontend/src/lib/types.ts` | Add `fulfilled_at` to `Order`, add `fulfilled_count`/`fulfilled_value` to `OrdersOverview` |
| `frontend/src/lib/api.ts` | Add `fulfilOrder(id)` call |
| `frontend/src/app/orders/page.tsx` | Add "Fulfilled" tab to filters. Show a "Mark Fulfilled" button on confirmed orders. |
| `frontend/src/app/page.tsx` | Add a "Fulfilled Today" KPI card |

### Proposed approach
Extend the order status lifecycle to:

```
pending_confirmation → confirmed → fulfilled
         ↓                ↓
       flagged          rejected
         ↓
       confirmed → fulfilled
```

1. **Approve** (existing flow, modified): Sets status to `confirmed`. Sends a **receipt confirmation** only: "Order received, [Customer]. We'll confirm delivery separately." No delivery date promise.

2. **Fulfil** (new flow): Sets status to `fulfilled`, records `fulfilled_at`. Sends a **delivery confirmation**: "Your order has been dispatched. Expected delivery: [date/time]." This is triggered by a new "Mark Fulfilled" button that appears on confirmed orders in the Order Queue.

3. **Frontend**: Add a "Fulfilled" tab. The "Confirmed" tab shows orders awaiting dispatch with a green "Mark Fulfilled" button. The overview page gains a new KPI card for fulfilled orders today.

### Complexity: Low–Medium
Mostly additive — a new endpoint, a new button, and splitting one message template into two.

---

## 3. Manual Response Option for User

### Current behaviour
All outbound messages to customers are auto-generated by the system. The wholesaler can only click Approve/Reject — there is no free-text input. If the wholesaler wants to say something custom (e.g., "We're running late today, delivery by 14:00 instead"), there is no mechanism.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/routers/orders.py` | Add `POST /api/orders/{id}/message` accepting `{ message: string }` |
| `backend/app/orchestrator.py` | Add `send_manual_message(order_id, message_text)` function |
| `backend/app/crud.py` | No change — `save_conversation` and `log_agent_action` already support this |
| `backend/app/whatsapp.py` | No change — `send_whatsapp_message` already exists |
| `frontend/src/lib/api.ts` | Add `sendManualMessage(orderId, message)` call |
| `frontend/src/app/orders/page.tsx` | Add a text input + "Send" button in the expanded order detail view |
| `backend/app/routers/customers.py` | Add `POST /api/customers/{id}/message` for sending messages not tied to a specific order |
| `frontend/src/app/customers/[id]/page.tsx` | Add a "Send Message" input at the bottom of the conversation history |

### Proposed approach

1. **Order-level manual message**: In the expanded order detail, add a text input below the order items. When submitted, the backend sends it via WhatsApp and logs it in `conversations` with `parsed_intent = "manual_message"`. This works for both pending and confirmed orders.

2. **Customer-level manual message**: On the customer detail page, add a text input below the conversation history. This allows the wholesaler to message a customer independent of any order (e.g., proactive communication).

3. Both endpoints reuse the existing `send_whatsapp_message()` and `save_conversation()` functions — no new infrastructure needed.

4. **For the fulfilment flow** (item #2): The "Mark Fulfilled" action can optionally include a custom message that overrides the default delivery template.

### Complexity: Low
This is mostly UI work — the backend already has all the necessary primitives.

---

## 4. Clarify Flagged Status in Order Queue

### Current behaviour
An order is flagged when the Customer Agent returns a non-empty `anomalies` list in its output. The flagging rules are defined only in the LLM system prompt ("If a quantity seems unusual — >3x their average — flag it as an anomaly") and in the fallback parser. When the LLM is unavailable, the fallback parser always adds "Fallback parser — items may not be accurate" as an anomaly, causing *every* fallback-parsed order to be flagged.

The frontend shows flagged orders in a "Flagged" tab, but there is no visible explanation of *why* the order was flagged.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/orchestrator.py` | When creating a flagged order, store the anomaly reasons in a structured way on the order itself (not just as alerts) |
| `backend/app/schema.py` | Add `flags_json TEXT` column to `orders` table to store flag reasons directly on the order |
| `backend/app/crud.py` | Update `create_order` to accept and store flags; update `get_order_by_id` to return them |
| `frontend/src/app/orders/page.tsx` | Display flag reasons as coloured badges on flagged orders (e.g., "Quantity anomaly: 500 instead of usual 50") |
| `frontend/src/lib/types.ts` | Add `flags: string[]` to `Order` type |
| `backend/app/customer_agent.py` | Make the fallback parser's anomaly message more specific; differentiate between "LLM unavailable" flags and genuine anomaly flags |

### Proposed approach

1. **Store flag reasons on the order**: Add a `flags_json` column to `orders`. When the orchestrator sets status to `flagged`, it serialises the anomaly list into this column. This means every flagged order carries its own explanation.

2. **Display in the UI**: On the Order Queue, flagged orders show their flag reasons as amber/red badges below the order summary. Examples:
   - "Quantity anomaly: Chicken Breast ordered 500kg (usual: 50kg)"
   - "Low confidence: parsed via fallback (LLM unavailable)"
   - "Unmatched product: 'the green stuff' could not be matched"

3. **User-defined flag rules** (stretch): Add a settings endpoint where the wholesaler can configure flag thresholds (e.g., flag if quantity > 2x average instead of 3x). For the hackathon, we can hardcode sensible defaults and note this as a production enhancement.

### Complexity: Low–Medium
The main work is adding the `flags_json` column and surfacing it in the UI. The data is already available — it just needs to be persisted and displayed.

---

## 5. Total Items to Be Fulfilled Overview

### Current behaviour
Each order shows its own line items, but there is no aggregate view. A wholesaler preparing to fulfil 10 orders has no way to see "I need 200kg chicken breast, 80kg potatoes, and 50L olive oil total across all pending orders."

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/crud.py` | Add `get_aggregated_items(status)` function that sums quantities across all orders of a given status, grouped by product |
| `backend/app/routers/orders.py` | Add `GET /api/orders/aggregate?status=confirmed` endpoint |
| `frontend/src/lib/api.ts` | Add `getAggregatedItems(status)` call |
| `frontend/src/lib/types.ts` | Add `AggregatedItem` type: `{ product_id, product_name, sku, category, unit, total_quantity, order_count }` |
| `frontend/src/components/Sidebar.tsx` | Add "Stock Overview" or "Fulfilment" nav item |
| New file: `frontend/src/app/fulfilment/page.tsx` | New page showing the aggregated items table |

### Proposed approach

1. **Backend query**: A single SQL query that JOINs `order_items` → `orders` → `products`, filters by order status (default: `confirmed` — i.e., orders accepted but not yet fulfilled), and `GROUP BY product_id` with `SUM(quantity)`.

2. **New sidebar page "Fulfilment"**: A table with columns: Product Name, SKU, Category, Unit, Total Quantity Needed, Number of Orders. Sortable by category or quantity. This gives the warehouse team a single pick list.
# Edit: Don't name it fulfilment, come up with a name that resembles "aggregate View" more

3. **Status filter**: A dropdown at the top to switch between "Confirmed" (default, orders to fulfil), "Pending" (preview of what's coming), or "All active" (pending + confirmed combined).

4. This page naturally complements the new `fulfilled` status from item #2 — once orders are marked fulfilled, their items drop off this list.

### Complexity: Low
One new SQL query, one new endpoint, one new page. The data already exists.

---

## 6. Message API Integration

### Current behaviour
The WhatsApp integration is structurally complete (webhook verification, inbound parsing, outbound sending) but requires real Meta WhatsApp Business API credentials. Without `META_WHATSAPP_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID` environment variables, `send_whatsapp_message()` logs a warning and returns `False` — messages are silently dropped.

The simulation endpoint (`POST /api/simulate/message`) works for testing the pipeline without real WhatsApp.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/whatsapp.py` | Potentially add fallback/mock mode that records messages in-app instead of silently dropping them |
| `backend/app/config.py` | No change needed — env vars are already defined |
| `.env` / `.env.example` | Document the required credentials and setup steps |

### Proposed approach

This is a **configuration/deployment task**, not a code change. The steps are:

1. **Meta Developer Account**: Create a Meta Developer account, register a WhatsApp Business app, and get API credentials.
2. **Configure webhook**: Point the Meta webhook URL to the deployed backend's `/webhook` endpoint. Set the `WHATSAPP_VERIFY_TOKEN` to match.
3. **Set environment variables**: `META_WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` in the deployment environment.
4. **Test phone number**: Meta provides a test phone number in the WhatsApp Business sandbox for development.

**Code improvement** (independent of credentials): Add a "message outbox" concept so that when WhatsApp credentials are missing, outbound messages are stored in a `message_outbox` table and displayed in the dashboard. This way the demo still shows what *would* have been sent, even without live WhatsApp. Currently these messages are only visible in the conversation log on the customer detail page — making them more prominent would help.

### Complexity: Low (code) / External dependency (credentials)

---

## 7. Full Units of Items Only (or Continuous Units)

### Current behaviour
All quantities are stored as `REAL` (floating point) in SQLite. The seed data applies a random `±20%` variation with `round(qty, 1)`, producing values like `16.4 bags` or `3.8 trays` — which makes no sense for indivisible units like bags, trays, boxes, bottles, cans, etc.

Products have a `unit` field (kg, L, pc, bottle, bag, box, tray, etc.) but there is **no distinction** between continuous units (kg, L) and discrete units (pc, bottle, bag, box, tray, can, jar, bunch, tub, pack).

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/schema.py` | Add `unit_type TEXT NOT NULL DEFAULT 'continuous'` to `products` table — values: `continuous` (kg, L) or `discrete` (pc, bottle, bag, etc.) |
| `backend/app/seed.py` | Set `unit_type` for each product. Apply `round(qty, 0)` for discrete units in the seed data. |
| `backend/app/crud.py` | Add a `validate_quantity(product_id, quantity)` function that rounds discrete-unit quantities to integers |
| `backend/app/customer_agent.py` | Include unit_type in the product catalogue search results so the LLM knows to output whole numbers for discrete items |
| `backend/app/orchestrator.py` | Call `validate_quantity` when creating orders to enforce rounding |
| `frontend/src/app/orders/page.tsx` | Display quantities as integers for discrete units (no decimal point) |

### Proposed approach

1. **Classify units**: Add a lookup mapping:
   - **Continuous** (allow decimals): `kg`, `L`
   - **Discrete** (integers only): `pc`, `bottle`, `bag`, `box`, `tray`, `can`, `jar`, `bunch`, `tub`, `pack`, `bucket`

2. **Backend validation**: When creating or updating order items, if the product's unit is discrete, round the quantity to the nearest integer. If the LLM outputs `3.7 bags`, store `4 bags`.

3. **Seed data fix**: Apply integer rounding for discrete units in the seed generation.

4. **Frontend display**: Format discrete quantities without decimal places (`4 bottles` not `4.0 bottles`).

### Complexity: Low
A small schema addition, a validation function, and formatting changes.

---

## 8. SKU Catalogue Discrepancy

### Current behaviour
When the Customer Agent parses a message, it fuzzy-matches product names to the catalogue and creates an order immediately. If the match is uncertain (low confidence), the order is flagged — but the customer is never asked to clarify. The wholesaler sees the parsed order and can approve/reject, but there's no mechanism to go back to the customer and say "Did you mean X or Y?"

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/orchestrator.py` | Add a `clarify_order` flow: when items have low confidence or are unmatched, send a clarification message to the customer instead of creating a pending order |
| `backend/app/customer_agent.py` | Return `unmatched_items` separately from `items` in the agent output |
| `backend/app/schema.py` | Add `needs_clarification` to order status values |
| `backend/app/crud.py` | Handle the new status |
| `backend/app/routers/orders.py` | Add `POST /api/orders/{id}/clarify` endpoint for the wholesaler to trigger a clarification message |
| `frontend/src/app/orders/page.tsx` | Show "Clarify" button on orders with low-confidence items; display which items are uncertain |
| `frontend/src/lib/api.ts` | Add `clarifyOrder(id, message)` call |

### Proposed approach

1. **Confidence threshold**: If any item in a parsed order has `matched_confidence < 0.7`, or if there are unmatched items, the order enters a `needs_clarification` status instead of `pending_confirmation`.

2. **Automatic clarification message**: The orchestrator sends a WhatsApp message listing the uncertain items: "We received your order but need to confirm a few items: You mentioned 'the green stuff' — did you mean Spinach Fresh (3.90/kg) or Broccoli (2.30/kg)? Please reply with your choice."

3. **Customer reply**: When the customer replies, the Customer Agent processes it with `modify_order` intent, resolving the ambiguity. The order then moves to `pending_confirmation`.

4. **Wholesaler-triggered clarification**: The wholesaler can also click "Clarify" on any pending/flagged order to send a custom clarification question to the customer.

5. **Order is not final until confirmed**: This reinforces the existing design principle — orders are proposals until the wholesaler clicks Approve.

### Complexity: Medium
Requires a new status, a new message flow, and handling the customer's reply as a modification. The Customer Agent already supports `modify_order` intent, so the reply handling is mostly wired up.

---

## 9. Manual Override of Order Details

### Current behaviour
The wholesaler can approve, reject, or substitute individual items, but cannot **edit** an order directly. If the wholesaler needs to change a quantity (e.g., the customer called to adjust) or add/remove an item, there's no mechanism.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/routers/orders.py` | Add `PUT /api/orders/{id}` endpoint accepting a modified items list |
| `backend/app/crud.py` | `update_order_items` already exists and can be reused; add `add_order_item` and `remove_order_item` for granular edits |
| `backend/app/orchestrator.py` | Log manual edits as agent actions with `agent_type: "wholesaler"` |
| `frontend/src/app/orders/page.tsx` | Add edit mode to the expanded order view: inline quantity editing, add/remove item buttons, save/cancel |
| `frontend/src/lib/api.ts` | Add `updateOrder(id, items)` call |
| `frontend/src/lib/types.ts` | No change needed — existing types cover this |

### Proposed approach

1. **Inline editing in the Order Queue**: When the wholesaler expands an order, each line item shows an edit icon. Clicking it makes the quantity field editable. A "Add Item" button at the bottom opens a product search dropdown. A delete icon on each item allows removal.

2. **Save changes**: When the wholesaler saves edits, the frontend sends the full updated items list to `PUT /api/orders/{id}`. The backend calls `update_order_items`, recalculates the total, resets the status to `pending_confirmation`, and logs the edit.

3. **Audit trail**: Every manual edit is logged in `agent_actions` with `agent_type: "wholesaler"`, `action: "manual_edit"`, and a `details_json` showing what changed (old vs new quantities, added/removed items).

4. **Status reset**: Any manual edit on a confirmed order moves it back to `pending_confirmation` to force re-approval. This prevents silent changes to already-confirmed orders.

### Complexity: Medium
The backend is straightforward (the CRUD function exists). The main effort is the frontend inline editing UI — quantity inputs, product search for adding items, and the save/cancel flow.

---

## 10. Multi-Channel Communication Tracking

### Current behaviour
The system only tracks WhatsApp messages that flow through the webhook. If the wholesaler speaks to a customer by phone, or the customer sends an email, or there's a conversation at the warehouse door — none of this is captured. The conversation history on the customer detail page only shows WhatsApp messages processed by the system.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/schema.py` | The `conversations` table already has a `channel` field — it just needs to support more values |
| `backend/app/routers/customers.py` | Add `POST /api/customers/{id}/note` endpoint for logging manual notes/calls/emails |
| `backend/app/crud.py` | `save_conversation` already accepts a `channel` parameter — just needs to be exposed |
| `frontend/src/app/customers/[id]/page.tsx` | Add a "Log Communication" form: channel dropdown (phone, email, in-person, other), free-text note, optional order linkage |
| `frontend/src/lib/api.ts` | Add `logCommunication(customerId, channel, note)` call |
| `frontend/src/lib/types.ts` | Extend `Conversation` type — already supports `channel` field |

### Proposed approach

1. **Manual communication logging**: On the customer detail page, add a "Log Communication" button that opens a form. The wholesaler selects the channel (Phone, Email, In-person, Other), types a note ("Customer called to say they need delivery by 9am instead of 10am"), and optionally links it to an order.

2. **Order-relevant detection**: When a logged communication mentions order-relevant keywords (quantities, product names, delivery changes), create an alert suggesting the wholesaler update the relevant order. For the MVP, this is a simple keyword match; in production, it could use the LLM.

3. **Conversation timeline**: The existing conversation history on the customer detail page already supports different channels via the `channel` field. Add distinct badge colours: WhatsApp (green), Phone (blue), Email (amber), In-person (grey), Other (grey).

4. **Future: email integration**: The architecture already supports adding email as an ingestion channel. The `channel` field on conversations and orders would be set to `email` instead of `whatsapp`. This is out of scope for now but the data model is ready.

### Complexity: Low–Medium
The data model already supports this. The main work is the frontend form and the optional keyword detection for order-relevant communication.

# Edit: Point 10 is a good point. Please keep it. On top of that, we would like to implement logging of outgoing messages. In other words, a customer texts the wholesaler via WhatsApp and that is played into the dashboard. Now, equally, the wholesaler can text the customer via WhatsApp back. This should also be logged in the application and, if relevant, affect the order details. For example, if outgoing message says "I will edit your order to 1 bag less of coffee" and the custoemr replies "Sounds good", the order should be adapted accordingly.

---

## Summary: Priority & Dependency Map

| # | Improvement | Complexity | Dependencies |
|---|------------|-----------|--------------|
| 2 | Fulfilment Differential | Low–Med | None — do this first, it changes the core order lifecycle |
| 4 | Clarify Flagged Status | Low–Med | None |
| 7 | Full Units Validation | Low | None |
| 5 | Aggregated Fulfilment Overview | Low | #2 (needs `fulfilled` status for full value) |
| 3 | Manual Response Option | Low | None |
| 9 | Manual Override of Order Details | Med | None |
| 6 | Message API Integration | Low/External | External (Meta credentials) |
| 1 | Health Score Clarification | Med | None, but benefits from #2 (more lifecycle events to track) |
| 8 | SKU Catalogue Discrepancy | Med | #3 (uses manual message for clarification) |
| 10 | Multi-Channel Communication | Low–Med | #3 (uses manual message infrastructure) |

### Recommended implementation order
1. **#2 Fulfilment Differential** — foundational lifecycle change, everything else builds on it
2. **#7 Full Units** + **#4 Flagged Clarification** — quick wins, fix data quality issues
3. **#5 Fulfilment Overview** — high-value feature, depends on #2
4. **#3 Manual Response** + **#9 Manual Override** — core UX improvements
5. **#6 Message API** — external dependency, pursue in parallel
6. **#1 Health Score** — richer once more lifecycle events exist
7. **#8 SKU Clarification** + **#10 Multi-Channel** — more complex flows, build on top of #3
