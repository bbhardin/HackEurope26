# Improvement Notes V1.1 — Response & Implementation Plan

This document addresses all 11 feedback items (the original 10 from `improvement_notes_v1.md` plus one new item). It incorporates the inline edits made to the V1 response.

**Changes from V1 response:**
- Item #5: Renamed from "Fulfilment" to **"Demand Overview"** per feedback
- Item #6: Updated — Meta WhatsApp Developer Key will be available before implementation; message outbox concept deprioritised
- Item #11: **New** — Bidirectional WhatsApp message logging with order-aware intent detection

---

## 1. Health Score Clarification for User

### Current behaviour
The health score is a static number (0.0–1.0) seeded per customer at database initialisation. It is **never recomputed** — no workflow updates it. The frontend displays it as a percentage with a three-tier colour label (Healthy / Watch / At Risk) but offers no explanation of *why* a customer has that score.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/schema.py` | Add a `customer_health_events` table to store individual health signals |
| `backend/app/crud.py` | Add functions to create health events and recompute the aggregate score |
| `backend/app/nudge_scheduler.py` | After detecting an overdue customer or declining order value, write a health event |
| `backend/app/orchestrator.py` | After order confirmation or rejection, write a health event |
| `frontend/src/app/customers/page.tsx` | Show the most recent health signal as a one-line reason underneath the score |
| `frontend/src/app/customers/[id]/page.tsx` | Add a "Health Timeline" section listing recent health events with severity badges |
| `frontend/src/lib/types.ts` | Add `HealthEvent` type |
| `frontend/src/lib/api.ts` | Add `getCustomerHealthEvents(id)` call |
| `backend/app/routers/customers.py` | Add `GET /api/customers/{id}/health-events` endpoint |

### Proposed approach
Replace the opaque 0–1 score with a **traffic-light system backed by observable events**:

1. **New table `customer_health_events`**: `(id, customer_id, event_type, severity, detail, created_at)`. Event types: `missed_order`, `declining_quantity`, `order_anomaly`, `returned_to_normal`. Severity: `info | warning | critical`.

2. **Dynamic recomputation**: Each time a health event is written, recompute the customer's `health_score` as a weighted rolling average over the last 28 days. Each `critical` event subtracts 0.15, each `warning` subtracts 0.05, each `info` (positive) adds 0.02, clamped to [0, 1].

3. **Frontend**: On the customer list, display the latest event as a short reason line (e.g., "Missed Tuesday order · 3 days ago"). On the customer detail page, show a scrollable health timeline. Replace the raw percentage with the traffic-light badge prominently, and show the percentage only as secondary text.

### Complexity: Medium

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
| `backend/app/orchestrator.py` | Split into two functions: `approve_order` (sends receipt confirmation) and `fulfil_order` (sends delivery message). Rewrite `generate_confirmation_message` to only confirm receipt. Add `generate_fulfilment_message`. |
| `backend/app/routers/orders.py` | Add `POST /api/orders/{id}/fulfil` endpoint |
| `frontend/src/lib/types.ts` | Add `fulfilled_at` to `Order`, add `fulfilled_count`/`fulfilled_value` to `OrdersOverview` |
| `frontend/src/lib/api.ts` | Add `fulfilOrder(id)` call |
| `frontend/src/app/orders/page.tsx` | Add "Fulfilled" tab. Show "Mark Fulfilled" button on confirmed orders. |
| `frontend/src/app/page.tsx` | Add a "Fulfilled Today" KPI card |

### Proposed approach
Extend the order status lifecycle:

```
pending_confirmation → confirmed → fulfilled
         ↓                ↓
       flagged          rejected
         ↓
       confirmed → fulfilled
```

1. **Approve** (modified): Sets status to `confirmed`. Sends a **receipt confirmation** only: "Order received, [Customer]. We'll notify you when it's dispatched."

2. **Fulfil** (new): Sets status to `fulfilled`, records `fulfilled_at`. Sends a **delivery notification**: "Your order has been dispatched. Expected delivery: [date/time]." Triggered by a new "Mark Fulfilled" button on confirmed orders.

3. **Frontend**: Add "Fulfilled" tab. Confirmed tab shows "Mark Fulfilled" button. Overview gains fulfilled KPI card.

### Complexity: Low–Medium

---

## 3. Manual Response Option for User

### Current behaviour
All outbound messages are auto-generated. The wholesaler can only click Approve/Reject — no free-text input. No mechanism for custom messages.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/routers/orders.py` | Add `POST /api/orders/{id}/message` accepting `{ message: string }` |
| `backend/app/orchestrator.py` | Add `send_manual_message(order_id, message_text)` function |
| `frontend/src/lib/api.ts` | Add `sendManualMessage(orderId, message)` call |
| `frontend/src/app/orders/page.tsx` | Add a text input + "Send" button in the expanded order detail view |
| `backend/app/routers/customers.py` | Add `POST /api/customers/{id}/message` for messages not tied to a specific order |
| `frontend/src/app/customers/[id]/page.tsx` | Add a "Send Message" input at the bottom of the conversation history |

### Proposed approach

1. **Order-level manual message**: Text input below order items in the expanded view. Sends via WhatsApp, logs in `conversations` with `parsed_intent = "manual_message"`.

2. **Customer-level manual message**: Text input below conversation history on customer detail page. Allows messaging independent of any order.

3. Both reuse existing `send_whatsapp_message()` and `save_conversation()` — no new infrastructure needed.

4. **For fulfilment** (item #2): "Mark Fulfilled" can optionally include a custom message overriding the default delivery template.

### Complexity: Low

---

## 4. Clarify Flagged Status in Order Queue

### Current behaviour
An order is flagged when the Customer Agent returns a non-empty `anomalies` list. The rules are in the LLM system prompt ("flag if >3x average") and in the fallback parser. The fallback parser always flags ("items may not be accurate"), causing every fallback-parsed order to be flagged. The frontend shows flagged orders but **no explanation of why**.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/orchestrator.py` | Store anomaly reasons on the order itself |
| `backend/app/schema.py` | Add `flags_json TEXT` column to `orders` table |
| `backend/app/crud.py` | Update `create_order` to accept and store flags; update `get_order_by_id` to return them |
| `frontend/src/app/orders/page.tsx` | Display flag reasons as coloured badges on flagged orders |
| `frontend/src/lib/types.ts` | Add `flags: string[]` to `Order` type |
| `backend/app/customer_agent.py` | Make fallback parser anomalies more specific; differentiate "LLM unavailable" from genuine anomalies |

### Proposed approach

1. **Store flag reasons on the order**: Add `flags_json` column to `orders`. Serialise the anomaly list when setting status to `flagged`.

2. **Display in UI**: Flagged orders show flag reasons as amber/red badges:
   - "Quantity anomaly: Chicken Breast ordered 500kg (usual: 50kg)"
   - "Low confidence: parsed via fallback (LLM unavailable)"
   - "Unmatched product: 'the green stuff' could not be matched"

3. **User-defined flag rules** (stretch): Settings endpoint for configurable thresholds. Hardcode sensible defaults for hackathon.

### Complexity: Low–Medium

---

## 5. Demand Overview (Aggregated Items)

### Current behaviour
Each order shows its own line items, but there is no aggregate view. A wholesaler preparing to fulfil 10 orders has no way to see "I need 200kg chicken breast total across all confirmed orders."

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/crud.py` | Add `get_aggregated_items(status)` function — sums quantities grouped by product |
| `backend/app/routers/orders.py` | Add `GET /api/orders/aggregate?status=confirmed` endpoint |
| `frontend/src/lib/api.ts` | Add `getAggregatedItems(status)` call |
| `frontend/src/lib/types.ts` | Add `AggregatedItem` type: `{ product_id, product_name, sku, category, unit, total_quantity, order_count }` |
| `frontend/src/components/Sidebar.tsx` | Add "Demand Overview" nav item |
| New file: `frontend/src/app/demand/page.tsx` | New page showing the aggregated items table |

### Proposed approach

1. **Backend query**: A single SQL query joining `order_items → orders → products`, filtering by order status, `GROUP BY product_id` with `SUM(quantity)`.

2. **New sidebar page "Demand Overview"**: A table with columns: Product Name, SKU, Category, Unit, Total Quantity Needed, Number of Orders. Sortable by category or quantity. This gives the warehouse team a consolidated view of total demand across all active orders.

3. **Status filter**: Dropdown to switch between "Confirmed" (default — accepted orders awaiting dispatch), "Pending" (preview of what's coming), or "All Active" (pending + confirmed combined).

4. This page complements the `fulfilled` status from item #2 — once orders are marked fulfilled, their items drop off this list.

### Complexity: Low

---

## 6. Message API Integration

### Current behaviour
The WhatsApp integration is structurally complete (webhook verification, inbound parsing, outbound sending) but requires real Meta WhatsApp Business API credentials. Without `META_WHATSAPP_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`, `send_whatsapp_message()` logs a warning and returns `False`.

### Status update
The Meta WhatsApp Developer Key is being procured and **will be available before implementing the revised version** specified in this document. This means:
- The integration can be tested with real credentials end-to-end
- The "message outbox" concept for credential-less demos becomes a nice-to-have rather than a necessity

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/whatsapp.py` | No structural change — already handles real API calls. May need minor adjustments once live credentials reveal any edge cases (e.g., rate limits, message template requirements). |
| `backend/app/config.py` | No change — env vars already defined |
| `.env` | Populate with real credentials once received |

### Remaining steps
1. Receive Meta WhatsApp Developer Key
2. Set `META_WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` in `.env`
3. Configure Meta webhook URL → deployed backend `/webhook`
4. Test with a real phone: send WhatsApp message → confirm it flows through the pipeline → confirm reply arrives back on phone
5. Adjust any message formatting if Meta's template rules require changes

### Complexity: Low (configuration only, once credentials arrive)

---

## 7. Full Units of Items Only (or Continuous Units)

### Current behaviour
All quantities are stored as `REAL` (floating point). Seed data applies ±20% variation with `round(qty, 1)`, producing values like `16.4 bags` or `3.8 trays` — nonsensical for indivisible units. No distinction between continuous units (kg, L) and discrete units (pc, bottle, bag, etc.).

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/schema.py` | Add `unit_type TEXT NOT NULL DEFAULT 'continuous'` to `products` table |
| `backend/app/seed.py` | Set `unit_type` per product. Apply `round(qty, 0)` for discrete units. |
| `backend/app/crud.py` | Add `validate_quantity(product_id, quantity)` — rounds discrete-unit quantities to integers |
| `backend/app/customer_agent.py` | Include `unit_type` in product catalogue search results so the LLM outputs whole numbers for discrete items |
| `backend/app/orchestrator.py` | Call `validate_quantity` when creating orders |
| `frontend/src/app/orders/page.tsx` | Display quantities as integers for discrete units |

### Proposed approach

1. **Classify units**:
   - **Continuous** (decimals allowed): `kg`, `L`
   - **Discrete** (integers only): `pc`, `bottle`, `bag`, `box`, `tray`, `can`, `jar`, `bunch`, `tub`, `pack`, `bucket`

2. **Backend validation**: On order creation/update, if the product's unit is discrete, round quantity to nearest integer (3.7 bags → 4 bags).

3. **Seed data fix**: Integer rounding for discrete units in seed generation.

4. **Frontend display**: No decimal places for discrete quantities.

### Complexity: Low

---

## 8. SKU Catalogue Discrepancy

### Current behaviour
The Customer Agent fuzzy-matches product names and creates an order immediately. Low-confidence matches are flagged but the customer is never asked to clarify. No mechanism for the wholesaler to say "Did you mean X or Y?"

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/orchestrator.py` | Add `clarify_order` flow for low-confidence/unmatched items |
| `backend/app/customer_agent.py` | Return `unmatched_items` separately from `items` |
| `backend/app/schema.py` | Add `needs_clarification` to order statuses |
| `backend/app/crud.py` | Handle new status |
| `backend/app/routers/orders.py` | Add `POST /api/orders/{id}/clarify` endpoint |
| `frontend/src/app/orders/page.tsx` | Show "Clarify" button on orders with low-confidence items |
| `frontend/src/lib/api.ts` | Add `clarifyOrder(id, message)` call |

### Proposed approach

1. **Confidence threshold**: If any item has `matched_confidence < 0.7` or there are unmatched items, the order enters `needs_clarification` status.

2. **Automatic clarification**: The orchestrator sends a WhatsApp message: "We received your order but need to confirm: You mentioned 'the green stuff' — did you mean Spinach Fresh (3.90/kg) or Broccoli (2.30/kg)?"

3. **Customer reply**: Processed by Customer Agent as `modify_order`, resolving the ambiguity. Order then moves to `pending_confirmation`.

4. **Wholesaler-triggered clarification**: "Clarify" button on any pending/flagged order to send a custom question.

5. **Orders are not final until confirmed**: Reinforces existing design principle.

### Complexity: Medium

---

## 9. Manual Override of Order Details

### Current behaviour
The wholesaler can approve, reject, or substitute individual items, but cannot edit an order directly — no mechanism to change quantities, add items, or remove items from the dashboard.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/routers/orders.py` | Add `PUT /api/orders/{id}` endpoint accepting a modified items list |
| `backend/app/crud.py` | `update_order_items` already exists; add `add_order_item` and `remove_order_item` for granular edits |
| `backend/app/orchestrator.py` | Log manual edits with `agent_type: "wholesaler"` |
| `frontend/src/app/orders/page.tsx` | Inline editing: editable quantity fields, add/remove item controls, save/cancel |
| `frontend/src/lib/api.ts` | Add `updateOrder(id, items)` call |

### Proposed approach

1. **Inline editing**: In the expanded order view, each line item shows an edit icon. Clicking makes quantity editable. "Add Item" button opens product search. Delete icon on each item.

2. **Save changes**: Frontend sends full updated items list to `PUT /api/orders/{id}`. Backend calls `update_order_items`, recalculates total, resets status to `pending_confirmation`.

3. **Audit trail**: Every edit logged in `agent_actions` with `agent_type: "wholesaler"`, `action: "manual_edit"`, `details_json` showing old vs new.

4. **Status reset**: Manual edit on a confirmed order moves it back to `pending_confirmation` to force re-approval.

### Complexity: Medium

---

## 10. Multi-Channel Communication Tracking

### Current behaviour
Only WhatsApp messages flowing through the webhook are tracked. Phone calls, emails, in-person conversations — none are captured. The conversation history only shows system-processed WhatsApp messages.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/schema.py` | `conversations` table already has `channel` field — just needs more values used |
| `backend/app/routers/customers.py` | Add `POST /api/customers/{id}/note` endpoint for logging off-platform communication |
| `backend/app/crud.py` | `save_conversation` already accepts a `channel` parameter |
| `frontend/src/app/customers/[id]/page.tsx` | Add "Log Communication" form: channel dropdown (Phone, Email, In-person, Other), free-text note, optional order linkage |
| `frontend/src/lib/api.ts` | Add `logCommunication(customerId, channel, note)` call |

### Proposed approach

1. **Manual communication logging**: "Log Communication" button on customer detail page. Form with channel dropdown, free-text note, optional order link.

2. **Order-relevant detection**: When logged communication mentions quantities/product names, create an alert suggesting the wholesaler update the relevant order. Simple keyword match for MVP; LLM-powered in production.

3. **Conversation timeline**: Distinct badge colours per channel: WhatsApp (green), Phone (blue), Email (amber), In-person (grey), Other (grey).

4. **Future: email integration**: Architecture already supports it via the `channel` field. Out of scope for now.

### Complexity: Low–Medium

---

## 11. Bidirectional WhatsApp Message Logging & Order-Aware Processing

### Current behaviour
The system currently processes **inbound customer messages** arriving via the Meta webhook. However, the wholesaler may also respond to customers **directly via WhatsApp** (using the WhatsApp Business app on their phone), bypassing the dashboard entirely. These wholesaler-originated messages are not captured, not displayed in the conversation history, and cannot trigger order changes.

This is a different problem from item #10 (off-platform channels like phone/email). Here, both sides of the conversation happen on WhatsApp — but only one side (customer → wholesaler) is captured.

### How Meta's webhook works
The Meta WhatsApp Cloud API webhook delivers **all message events** for the business phone number, including:
- `messages` — inbound messages from customers (already handled)
- `messages` — messages sent by the business (if the business replies via the WhatsApp app, Meta delivers a webhook notification with `"statuses"` updates, but the **message content itself** is only available if the business uses the Cloud API to send)

**Key technical constraint**: If the wholesaler replies via the WhatsApp mobile app (not through our API), Meta's webhook does **not** deliver the outbound message content — only delivery status updates (`sent`, `delivered`, `read`). To capture the actual text of outbound messages, the wholesaler must send them **through our system** (either via the dashboard's manual message feature from item #3, or via the Cloud API).

This means the implementation has two parts:
- **Part A**: Log all messages sent through our system (already partially done — `save_conversation` is called on most outbound messages, but not consistently)
- **Part B**: When an outbound message is order-relevant, detect this and propose/apply order changes

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/orchestrator.py` | Ensure every outbound message is logged via `save_conversation` (audit existing calls). Add `analyse_outbound_for_order_impact` function. |
| `backend/app/customer_agent.py` | Add an `analyse_message_for_order_changes` mode that takes a wholesaler's outbound message and detects if it implies order modifications |
| `backend/app/pipeline.py` | Add a handler for wholesaler-to-customer messages that checks for order-relevant content |
| `backend/app/routers/orders.py` | Extend `POST /api/orders/{id}/message` (from item #3) to also run order-impact analysis on the sent message |
| `backend/app/crud.py` | No structural change — existing functions cover this |
| `frontend/src/app/orders/page.tsx` | After sending a manual message, show a prompt if the system detected an order-relevant change: "It looks like you mentioned removing 1 bag of coffee. Apply this change to the order?" |
| `frontend/src/app/customers/[id]/page.tsx` | Conversation timeline shows all outbound messages (both auto-generated and manual) with distinct styling |
| `frontend/src/lib/types.ts` | Add `source: "system" | "manual"` to `Conversation` type to distinguish auto vs manual messages |

### Proposed approach

**Part A — Consistent outbound logging:**

1. Audit every call to `send_whatsapp_message()` and ensure a corresponding `save_conversation(..., direction="outbound")` follows. Currently most paths do this, but the nudge scheduler and some edge cases may not.

2. Add a `source` field to the `conversations` table (`system` for auto-generated, `manual` for wholesaler-typed messages). Display these differently in the UI.

**Part B — Order-aware outbound analysis:**

1. When the wholesaler sends a manual message via the dashboard (using the text input from item #3), pass the message through the Customer Agent in a special "analyse mode":
   - Input: the outbound message text + the customer's context + their pending/confirmed orders
   - Output: a structured assessment — did this message imply an order change? If so, what change?

2. If a change is detected (e.g., "I will edit your order to 1 bag less of coffee"), the system:
   - Shows a confirmation prompt in the UI: "Detected order change: Remove 1x Espresso Beans 1kg from order ORD-xxx. Apply?"
   - If the wholesaler confirms, the order items are updated automatically
   - The change is logged as `agent_type: "orchestrator"`, `action: "outbound_message_edit"`

3. When the **customer replies** confirming (e.g., "Sounds good"), the inbound pipeline processes it normally. If there's a pending order in `needs_clarification` or `pending_confirmation`, the Customer Agent recognises it as a confirmation and the order stays/moves to `pending_confirmation`.

**Part C — Handling replies from the WhatsApp app (stretch):**

If the wholesaler replies directly via their WhatsApp phone app (not through the dashboard), the message content is **not** available via the webhook. Options:
- **Accept the limitation**: Encourage wholesalers to use the dashboard for messaging. The manual message feature (item #3) makes this convenient.
- **WhatsApp Business Platform workaround**: Use the "conversation" webhook field to detect that a conversation was initiated by the business, and prompt the wholesaler in the dashboard: "It looks like you replied to [Customer] directly via WhatsApp. Please log the content of your message so we can track it."
- **Long-term**: Migrate to the WhatsApp Business API "on-premises" deployment where all messages flow through the business server. This is out of scope for the hackathon.

### Example flow

1. **Wholesaler** reviews an order from Chef Meyer on the dashboard. Notices they're running low on coffee.
2. **Wholesaler** types in the manual message box: "Hi Chef Meyer, we're running low on Espresso Beans. I'll adjust your order to remove the 3kg of beans. We should have it restocked by Thursday."
3. **System** sends the message via WhatsApp. Also analyses the text and detects: "remove Espresso Beans from this order."
4. **Dashboard** shows a prompt: "Detected change: Remove 3kg Espresso Beans 1kg (EUR 14.50/kg) from order ORD-abc. Apply this change?"
5. **Wholesaler** clicks "Apply". The order is updated, total recalculated.
6. **Chef Meyer** replies on WhatsApp: "No problem, thanks for letting me know."
7. **System** processes the inbound reply. Customer Agent classifies it as `general_inquiry` (acknowledgment, no action needed). Logged in conversation history.

### Complexity: Medium–High
Part A (consistent logging) is low complexity. Part B (order-aware analysis) is medium — it reuses the Customer Agent's LLM capabilities in a new context. Part C (WhatsApp app replies) has inherent platform limitations.

---

## Summary: Priority & Dependency Map

| # | Improvement | Complexity | Dependencies |
|---|------------|-----------|--------------|
| 2 | Fulfilment Differential | Low–Med | None — do this first, it changes the core order lifecycle |
| 4 | Clarify Flagged Status | Low–Med | None |
| 7 | Full Units Validation | Low | None |
| 6 | Message API Integration | Low | External (Meta credentials — arriving soon) |
| 5 | Demand Overview | Low | #2 (benefits from `fulfilled` status) |
| 3 | Manual Response Option | Low | #6 (needs working WhatsApp to be useful) |
| 9 | Manual Override of Order Details | Med | None |
| 1 | Health Score Clarification | Med | None, but benefits from #2 (more lifecycle events) |
| 10 | Multi-Channel Communication | Low–Med | #3 (uses manual message infrastructure) |
| 8 | SKU Catalogue Discrepancy | Med | #3 (uses manual message for clarification) |
| 11 | Bidirectional WhatsApp Logging | Med–High | #3 (needs manual message feature), #6 (needs live WhatsApp), #9 (needs order editing) |

### Recommended implementation order

1. **#2 Fulfilment Differential** — foundational lifecycle change, everything else builds on it
2. **#7 Full Units** + **#4 Flagged Clarification** — quick wins, fix data quality issues
3. **#6 Message API** — configure credentials once received (unblocks #3, #11)
4. **#5 Demand Overview** + **#3 Manual Response** — high-value features, now possible with working WhatsApp
5. **#9 Manual Override** — core UX improvement for order editing
6. **#1 Health Score** — richer once more lifecycle events exist
7. **#10 Multi-Channel** + **#8 SKU Clarification** — build on top of #3
8. **#11 Bidirectional WhatsApp Logging** — builds on #3, #6, and #9; most complex item, do last
