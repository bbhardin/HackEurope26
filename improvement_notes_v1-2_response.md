# Improvement Notes V1.2 — Response & Implementation Plan

This document addresses all 11 feedback items (the original 10 from `improvement_notes_v1.md` plus one new item). It incorporates all inline edits from V1 and V1.1 reviews.

**Changes from V1.1 response:**
- Item #11: Removed Part C (WhatsApp app replies). Scope is now Part A (consistent outbound logging) + Part B (order-aware outbound analysis) only. Complexity reduced from Medium–High to Medium.

**Carried forward from V1.1:**
- Item #5: Named **"Demand Overview"** (not "Fulfilment")
- Item #6: Meta WhatsApp Developer Key will be available before implementation
- Item #11: New — Bidirectional WhatsApp message logging with order-aware intent detection (Parts A + B)

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
| `backend/app/whatsapp.py` | No structural change — already handles real API calls. May need minor adjustments once live credentials reveal any edge cases. |
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
The system processes **inbound customer messages** via the Meta webhook. However, the wholesaler may also send messages to customers **through the dashboard** (once item #3 is implemented). These outbound messages need to be:
- Consistently logged in the conversation history
- Analysed for order-relevant content (e.g., "I'll remove 1 bag of coffee from your order")
- Acted upon when they imply order changes

### Scope
**Part A**: Consistent outbound logging — ensure every message sent through our system is recorded with a `source` field distinguishing auto-generated vs manually-typed messages.

**Part B**: Order-aware outbound analysis — when the wholesaler sends a manual message, detect if it implies an order change and offer to apply it automatically.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/schema.py` | Add `source TEXT NOT NULL DEFAULT 'system'` to `conversations` table (values: `system`, `manual`) |
| `backend/app/orchestrator.py` | Audit all `save_conversation` calls to ensure consistent logging. Add `analyse_outbound_for_order_impact()` function. |
| `backend/app/customer_agent.py` | Add `analyse_message_for_order_changes` mode — takes an outbound message + customer context + pending orders, returns structured assessment of implied order changes |
| `backend/app/pipeline.py` | Add handler for wholesaler-to-customer messages that runs order-impact analysis |
| `backend/app/routers/orders.py` | Extend `POST /api/orders/{id}/message` (from item #3) to return detected order changes in the response |
| `backend/app/routers/customers.py` | Extend `POST /api/customers/{id}/message` (from item #3) to also run order-impact analysis |
| `frontend/src/app/orders/page.tsx` | After sending a manual message, show a confirmation prompt if the system detected an order change: "It looks like you mentioned removing 1 bag of coffee. Apply this change to the order?" |
| `frontend/src/app/customers/[id]/page.tsx` | Conversation timeline shows all outbound messages with distinct styling for system vs manual |
| `frontend/src/lib/types.ts` | Add `source: "system" \| "manual"` to `Conversation` type. Add `DetectedOrderChange` type for the analysis response. |
| `frontend/src/lib/api.ts` | Update `sendManualMessage` return type to include detected changes |

### Proposed approach

**Part A — Consistent outbound logging:**

1. Audit every call to `send_whatsapp_message()` across the codebase and ensure a corresponding `save_conversation(..., direction="outbound")` follows. Currently most paths do this, but the nudge scheduler and some edge cases may not.

2. Add a `source` column to the `conversations` table:
   - `system` — auto-generated messages (confirmations, nudges, clarifications)
   - `manual` — wholesaler-typed messages via the dashboard

3. Display these differently in the conversation timeline UI: system messages get a subtle "auto" tag, manual messages show as regular outbound messages.

**Part B — Order-aware outbound analysis:**

1. When the wholesaler sends a manual message via the dashboard (the text input from item #3), the backend:
   - Sends the message via WhatsApp
   - Logs it in `conversations` with `source = "manual"`
   - Passes the message through the Customer Agent in an **"analyse outbound" mode**:
     - Input: the outbound message text + customer context + their pending/confirmed orders
     - Output: a structured assessment — did this message imply an order change? If so: which order, which items, what modification (add/remove/change quantity)?

2. The API response from `POST /api/orders/{id}/message` includes the detected changes (if any):
   ```json
   {
     "status": "sent",
     "detected_changes": [
       {
         "order_id": "ord-abc",
         "action": "remove_item",
         "product_name": "Espresso Beans 1kg",
         "product_id": "prod-bev-008",
         "quantity_change": -1,
         "confidence": 0.92
       }
     ]
   }
   ```

3. The frontend receives this response. If `detected_changes` is non-empty, it shows a confirmation prompt:
   > "Detected order change: Remove 1x Espresso Beans 1kg (EUR 14.50) from order ORD-abc. **Apply?**"

4. If the wholesaler clicks "Apply", the frontend calls `PUT /api/orders/{id}` (from item #9) with the updated items. The change is logged with `agent_type: "orchestrator"`, `action: "outbound_message_edit"`.

5. If the wholesaler dismisses the prompt, no order change is made — the message was sent but the order stays as-is.

6. When the **customer replies** (e.g., "Sounds good"), the inbound pipeline processes it normally. The Customer Agent classifies it as `general_inquiry` (acknowledgment) or `repeat_order` (confirmation). No special handling needed — the existing pipeline covers this.

### Example flow

1. **Wholesaler** reviews Chef Meyer's order on the dashboard. Notices they're running low on coffee.
2. **Wholesaler** types in the manual message box: "Hi Chef Meyer, we're running low on Espresso Beans. I'll adjust your order to remove the 3kg of beans. We should have it restocked by Thursday."
3. **System** sends the message via WhatsApp. Analyses the text and detects: "remove Espresso Beans from this order."
4. **Dashboard** shows a prompt: "Detected change: Remove 3kg Espresso Beans 1kg (EUR 14.50/kg) from order ORD-abc. Apply this change?"
5. **Wholesaler** clicks "Apply". The order is updated, total recalculated.
6. **Chef Meyer** replies on WhatsApp: "No problem, thanks for letting me know."
7. **System** processes the inbound reply. Customer Agent classifies as `general_inquiry` (acknowledgment, no action needed). Logged in conversation history.

### Complexity: Medium
Part A (consistent logging + source field) is low complexity. Part B (order-aware analysis) is medium — it reuses the Customer Agent's LLM capabilities in a new "analyse outbound" context, and requires a confirmation prompt in the frontend.

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
| 11 | Bidirectional WhatsApp Logging | Med | #3 (needs manual message feature), #6 (needs live WhatsApp), #9 (needs order editing for "Apply" flow) |

### Recommended implementation order

1. **#2 Fulfilment Differential** — foundational lifecycle change, everything else builds on it
2. **#7 Full Units** + **#4 Flagged Clarification** — quick wins, fix data quality issues
3. **#6 Message API** — configure credentials once received (unblocks #3, #11)
4. **#5 Demand Overview** + **#3 Manual Response** — high-value features, now possible with working WhatsApp
5. **#9 Manual Override** — core UX improvement for order editing
6. **#1 Health Score** — richer once more lifecycle events exist
7. **#10 Multi-Channel** + **#8 SKU Clarification** — build on top of #3
8. **#11 Bidirectional WhatsApp Logging** — builds on #3, #6, and #9; implement last

---
---

## Detailed Implementation Todo List

Organised into 8 phases following the recommended implementation order. Each phase groups related improvements. Within each phase, tasks are listed in dependency order — earlier tasks must complete before later ones.

---

### Phase A: Fulfilment Differential (Improvement #2)
> Goal: Extend the order lifecycle with a `fulfilled` status, split the confirmation message from the delivery message, and add a "Mark Fulfilled" button.

**Backend:**

- [x] **A.1** Schema: Add `fulfilled_at TEXT` column to `orders` table. Update the status comment to include `fulfilled`.
  - File: `backend/app/schema.py`

- [x] **A.2** CRUD: Update `update_order_status()` to set `fulfilled_at = datetime.now()` when status is `fulfilled`. Add `get_orders_overview()` counts/values for fulfilled orders (fulfilled_count, fulfilled_value, fulfilled_today_count, fulfilled_today_value).
  - File: `backend/app/crud.py`

- [x] **A.3** Orchestrator: Rewrite `generate_confirmation_message()` to only confirm receipt — remove the "Delivery: Next business day" line. Replace with: "Order received, [Customer]. We'll notify you when it's dispatched." Keep the line-item breakdown.
  - File: `backend/app/orchestrator.py`

- [x] **A.4** Orchestrator: Add `generate_fulfilment_message(order)` — produces a delivery notification: "Your order has been dispatched, [Customer]. Expected delivery: [date/time]." with the same line-item breakdown.
  - File: `backend/app/orchestrator.py`

- [x] **A.5** Orchestrator: Add `fulfil_order(order_id)` async function — calls `update_order_status(order_id, "fulfilled")`, generates fulfilment message, sends via WhatsApp, logs to conversations and agent_actions.
  - File: `backend/app/orchestrator.py`

- [x] **A.6** Router: Add `POST /api/orders/{id}/fulfil` endpoint. Validate that order status is `confirmed` before allowing fulfilment. Call `fulfil_order()`.
  - File: `backend/app/routers/orders.py`

**Frontend:**

- [x] **A.7** Types: Add `fulfilled_at: string | null` to `Order`. Add `fulfilled_count`, `fulfilled_value`, `fulfilled_today_count`, `fulfilled_today_value` to `OrdersOverview`.
  - File: `frontend/src/lib/types.ts`

- [x] **A.8** API: Add `fulfilOrder(id: string)` function calling `POST /api/orders/{id}/fulfil`.
  - File: `frontend/src/lib/api.ts`

- [x] **A.9** Order Queue: Add "Fulfilled" to the filter tabs. Show a blue "Mark Fulfilled" button on orders with status `confirmed`. Clicking calls `fulfilOrder()` and refreshes.
  - File: `frontend/src/app/orders/page.tsx`

- [x] **A.10** Overview: Add a "Fulfilled Today" KPI card showing `fulfilled_today_count` and `fulfilled_today_value`. Rearrange grid to 5 cards or keep 4 and replace the "Total Confirmed" card with "Fulfilled Today".
  - File: `frontend/src/app/page.tsx`

- [x] **A.11** Seed data: Update some historical orders to have status `fulfilled` with `fulfilled_at` timestamps so the dashboard isn't empty on first load.
  - File: `backend/app/seed.py`

- [x] **A.12** Typecheck: Run `npx tsc --noEmit` to confirm no type errors introduced.

---

### Phase B: Data Quality — Full Units (#7) + Flagged Clarification (#4)
> Goal: Fix nonsensical decimal quantities for discrete units. Make flagged order reasons visible.

**Improvement #7 — Full Units:**

- [x] **B.1** Schema: Add `unit_type TEXT NOT NULL DEFAULT 'continuous'` column to `products` table. Values: `continuous` (kg, L) or `discrete` (pc, bottle, bag, box, tray, can, jar, bunch, tub, pack, bucket).
  - File: `backend/app/schema.py`

- [x] **B.2** Seed: For each product in `CATEGORIES`, assign the correct `unit_type` based on its unit. Update the `seed_products()` function to insert `unit_type`. Update `seed_order_history()` to round quantities to integers for discrete-unit products.
  - File: `backend/app/seed.py`

- [x] **B.3** CRUD: Add `get_product_unit_type(product_id) -> str` helper. Add `validate_quantity(product_id, quantity) -> float` that rounds to int if the product's unit is discrete, returns as-is if continuous.
  - File: `backend/app/crud.py`

- [x] **B.4** Orchestrator: In `_handle_order_intent()`, call `validate_quantity()` on each item's quantity before passing to `create_order()`.
  - File: `backend/app/orchestrator.py`

- [x] **B.5** Customer Agent: In `_execute_tool()` for `search_product_catalogue`, include `unit_type` in the returned product data so the LLM knows to output whole numbers for discrete items.
  - File: `backend/app/customer_agent.py`

- [x] **B.6** Frontend: In the Order Queue item table, format quantities without decimals when the item's unit is discrete. This requires the `unit_type` field to be available on `OrderItem` — either add it to the type, or infer from the unit string on the frontend using the same continuous/discrete mapping.
  - File: `frontend/src/app/orders/page.tsx`, `frontend/src/lib/types.ts`

**Improvement #4 — Flagged Clarification:**

- [x] **B.7** Schema: Add `flags_json TEXT` column to `orders` table (nullable, default NULL).
  - File: `backend/app/schema.py`

- [x] **B.8** CRUD: Update `create_order()` to accept an optional `flags: list[str]` parameter and store it as JSON in `flags_json`. Update `get_order_by_id()` to parse and return `flags_json` as a list.
  - File: `backend/app/crud.py`

- [x] **B.9** Orchestrator: In `_handle_order_intent()`, pass the `anomalies` list from the agent output to `create_order(..., flags=anomalies)`. Also pass the `notes` field if non-empty.
  - File: `backend/app/orchestrator.py`

- [x] **B.10** Customer Agent: In the fallback parser, differentiate flag types. Instead of the generic "Fallback parser — items may not be accurate", use specific messages: "Low confidence: order parsed without LLM (fallback mode)". For genuine anomalies, prefix with "Quantity anomaly:" or "Unmatched product:".
  - File: `backend/app/customer_agent.py`

- [x] **B.11** Frontend types: Add `flags: string[] | null` to the `Order` type.
  - File: `frontend/src/lib/types.ts`

- [x] **B.12** Frontend Order Queue: When an order has non-empty `flags`, display them as amber/red badges below the order summary line. Show before the expand/collapse area so they're visible at a glance.
  - File: `frontend/src/app/orders/page.tsx`

- [x] **B.13** Re-seed and typecheck: Run `python -m app.seed` to regenerate demo data with integer quantities for discrete units. Run `npx tsc --noEmit`.

---

### Phase C: Message API Integration (#6)
> Goal: Configure real Meta WhatsApp credentials and verify end-to-end message flow.

- [x] **C.1** Receive Meta WhatsApp Developer Key and Phone Number ID from the team.

- [x] **C.2** Populate `backend/.env` with `META_WHATSAPP_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`.

- [x] **C.3** Deploy the backend (Railway/Fly.io) and configure the Meta webhook URL to point to the deployed `/webhook` endpoint. Set `WHATSAPP_VERIFY_TOKEN` to match.

- [x] **C.4** Test webhook verification: confirm Meta's verification GET request succeeds.

- [x] **C.5** Test inbound: send a WhatsApp message from a real phone to the business number. Confirm it arrives at the webhook, flows through the pipeline, and creates a pending order on the dashboard.

- [x] **C.6** Test outbound: approve the order on the dashboard. Confirm the WhatsApp confirmation message arrives on the real phone.

- [x] **C.7** If Meta's message template rules require pre-approved templates for business-initiated messages, adjust `send_whatsapp_message()` in `backend/app/whatsapp.py` to use template messages where required (e.g., for nudges, which are business-initiated outside the 24h conversation window).

---

### Phase D: Demand Overview (#5) + Manual Response (#3)
> Goal: Add the aggregated demand page and enable manual messaging from the dashboard.

**Improvement #5 — Demand Overview:**

- [x] **D.1** CRUD: Add `get_aggregated_items(statuses: list[str]) -> list[dict]` — SQL query joining `order_items → orders → products`, filtering by order status IN (statuses), GROUP BY product_id, returning product_name, sku, category, unit, SUM(quantity) as total_quantity, COUNT(DISTINCT order_id) as order_count.
  - File: `backend/app/crud.py`

- [x] **D.2** Router: Add `GET /api/orders/aggregate` endpoint with optional `status` query param (default: `confirmed`). Supports comma-separated statuses like `?status=confirmed,pending_confirmation`.
  - File: `backend/app/routers/orders.py`

- [x] **D.3** Frontend types: Add `AggregatedItem` interface: `{ product_id: string, product_name: string, sku: string, category: string, unit: string, total_quantity: number, order_count: number }`.
  - File: `frontend/src/lib/types.ts`

- [x] **D.4** Frontend API: Add `getAggregatedItems(status?: string): Promise<AggregatedItem[]>` calling `GET /api/orders/aggregate`.
  - File: `frontend/src/lib/api.ts`

- [x] **D.5** Sidebar: Add "Demand Overview" nav item with route `/demand` and icon "▤".
  - File: `frontend/src/components/Sidebar.tsx`

- [x] **D.6** New page: Create `frontend/src/app/demand/page.tsx`. Table with columns: Product Name, SKU, Category, Unit, Total Qty, Orders. Status filter dropdown at top (Confirmed / Pending / All Active). Auto-refresh every 5 seconds.
  - File: `frontend/src/app/demand/page.tsx` (new)

**Improvement #3 — Manual Response:**

- [x] **D.7** Orchestrator: Add `send_manual_message(customer_id, message_text, order_id=None)` async function. Sends via WhatsApp, logs to conversations with `parsed_intent = "manual_message"`, logs to agent_actions with `agent_type = "wholesaler"`.
  - File: `backend/app/orchestrator.py`

- [x] **D.8** Router (orders): Add `POST /api/orders/{id}/message` endpoint accepting `{ message: string }`. Looks up the order's customer, calls `send_manual_message()`.
  - File: `backend/app/routers/orders.py`

- [x] **D.9** Router (customers): Add `POST /api/customers/{id}/message` endpoint accepting `{ message: string }`. Calls `send_manual_message()` without an order_id.
  - File: `backend/app/routers/customers.py`

- [x] **D.10** Frontend API: Add `sendOrderMessage(orderId: string, message: string)` and `sendCustomerMessage(customerId: string, message: string)`.
  - File: `frontend/src/lib/api.ts`

- [x] **D.11** Frontend Order Queue: In the expanded order detail view, add a text input and "Send Message" button below the order items. On submit, call `sendOrderMessage()`, clear input, show brief success toast.
  - File: `frontend/src/app/orders/page.tsx`

- [x] **D.12** Frontend Customer Detail: Add a text input and "Send" button at the bottom of the conversation history section. On submit, call `sendCustomerMessage()`, clear input, reload conversations.
  - File: `frontend/src/app/customers/[id]/page.tsx`

- [x] **D.13** Fulfilment + Manual Message integration: Update the "Mark Fulfilled" button to optionally show a text input for a custom delivery message. If empty, use the default `generate_fulfilment_message()`. If filled, use the custom text instead.
  - File: `frontend/src/app/orders/page.tsx`, `backend/app/routers/orders.py` (add optional `message` body param to `/fulfil`)

- [x] **D.14** Typecheck: Run `npx tsc --noEmit`.

---

### Phase E: Manual Override of Order Details (#9)
> Goal: Allow the wholesaler to edit order items directly from the dashboard.

- [x] **E.1** Router: Add `PUT /api/orders/{id}` endpoint accepting `{ items: [{ product_id, quantity, unit_price }] }`. Validates the order exists. Calls `update_order_items()`. Logs the edit in `agent_actions` with `agent_type: "wholesaler"`, `action: "manual_edit"`. If order was `confirmed`, resets to `pending_confirmation`.
  - File: `backend/app/routers/orders.py`

- [x] **E.2** Router: Add `GET /api/products` endpoint (if not already present) returning all products for the product search dropdown. Also add `GET /api/products/search?q=...` for filtered search.
  - File: `backend/app/routers/orders.py` or new `backend/app/routers/products.py`

- [x] **E.3** Frontend API: Add `updateOrderItems(orderId: string, items: EditableItem[])` calling `PUT /api/orders/{id}`. Add `searchProducts(query: string)` calling `GET /api/products/search`.
  - File: `frontend/src/lib/api.ts`

- [x] **E.4** Frontend types: Add `EditableItem` interface: `{ product_id: string, quantity: number, unit_price: number }`. Add `Product` interface if not present.
  - File: `frontend/src/lib/types.ts`

- [x] **E.5** Frontend Order Queue — Edit mode: In the expanded order detail, add an "Edit" button that toggles edit mode. In edit mode:
  - Each quantity cell becomes an input field
  - Each row shows a delete (X) button
  - An "Add Item" row appears at the bottom with a product search input
  - "Save" and "Cancel" buttons replace Approve/Reject
  - On Save: call `updateOrderItems()`, exit edit mode, refresh
  - On Cancel: discard changes, exit edit mode
  - File: `frontend/src/app/orders/page.tsx`

- [x] **E.6** Typecheck: Run `npx tsc --noEmit`.

---

### Phase F: Health Score Clarification (#1)
> Goal: Replace the static health score with an event-driven system that explains *why* a customer's health is what it is.

- [x] **F.1** Schema: Add `customer_health_events` table: `(id TEXT PK, customer_id TEXT FK, event_type TEXT, severity TEXT, detail TEXT, created_at TEXT)`.
  - File: `backend/app/schema.py`

- [x] **F.2** CRUD: Add `create_health_event(customer_id, event_type, severity, detail)` — inserts a health event and then calls `recompute_health_score(customer_id)`. Add `recompute_health_score(customer_id)` — queries health events from the last 28 days, applies the weighted formula (critical: -0.15, warning: -0.05, info: +0.02), clamps to [0,1], updates `customers.health_score`. Add `get_health_events(customer_id, limit=20)`.
  - File: `backend/app/crud.py`

- [x] **F.3** Nudge Scheduler: After detecting an overdue customer, call `create_health_event(customer_id, "missed_order", "warning", "Overdue by {days} days on usual {day} order")`. For high-risk churn (7+ days), use severity `critical`.
  - File: `backend/app/nudge_scheduler.py`

- [x] **F.4** Orchestrator: After `approve_order()`, call `create_health_event(customer_id, "returned_to_normal", "info", "Order confirmed")`. After `reject_order()`, call `create_health_event(customer_id, "order_anomaly", "warning", "Order rejected")`.
  - File: `backend/app/orchestrator.py`

- [x] **F.5** Router: Add `GET /api/customers/{id}/health-events` endpoint returning `get_health_events(customer_id)`.
  - File: `backend/app/routers/customers.py`

- [x] **F.6** Seed: Generate health events for each customer based on their seeded order history. Customers with low health scores should have some `missed_order` events. Run `recompute_health_score()` for each customer at the end of seeding.
  - File: `backend/app/seed.py`

- [x] **F.7** Frontend types: Add `HealthEvent` interface: `{ id: string, customer_id: string, event_type: string, severity: string, detail: string, created_at: string }`.
  - File: `frontend/src/lib/types.ts`

- [x] **F.8** Frontend API: Add `getHealthEvents(customerId: string): Promise<HealthEvent[]>`.
  - File: `frontend/src/lib/api.ts`

- [x] **F.9** Frontend Customer List: Below the health score percentage, show the most recent health event as a one-line summary. E.g., "Missed Tuesday order · 3 days ago" in amber, or "Order confirmed · today" in green.
  - File: `frontend/src/app/customers/page.tsx`

- [x] **F.10** Frontend Customer Detail: Add a "Health Timeline" section (below the context section, above orders/conversations). Scrollable list of health events with severity badges (green for info, amber for warning, red for critical), event type, detail text, and relative timestamp.
  - File: `frontend/src/app/customers/[id]/page.tsx`

- [x] **F.11** Typecheck: Run `npx tsc --noEmit`.

---

### Phase G: Multi-Channel Tracking (#10) + SKU Clarification (#8)
> Goal: Enable logging of off-platform communication. Add a clarification flow for uncertain product matches.

**Improvement #10 — Multi-Channel Communication:**

- [x] **G.1** Router: Add `POST /api/customers/{id}/note` endpoint accepting `{ channel: string, message: string, order_id?: string }`. Calls `save_conversation(customer_id, "inbound", message, "manual_note", channel)`. If `order_id` is provided, also creates an alert linking the note to that order.
  - File: `backend/app/routers/customers.py`

- [x] **G.2** Frontend API: Add `logCommunication(customerId: string, channel: string, message: string, orderId?: string)`.
  - File: `frontend/src/lib/api.ts`

- [x] **G.3** Frontend Customer Detail: Add a "Log Communication" button that expands a form: channel dropdown (Phone, Email, In-person, Other), free-text note, optional order ID dropdown (populated from customer's recent orders). On submit, call `logCommunication()`, collapse form, reload conversations.
  - File: `frontend/src/app/customers/[id]/page.tsx`

- [x] **G.4** Frontend Conversation Timeline: Update badge colours per channel. Currently all show WhatsApp badges. Add: Phone (blue), Email (amber), In-person (grey), Other (grey). Differentiate the "manual_note" parsed_intent from regular messages with a "Note" label.
  - File: `frontend/src/app/customers/[id]/page.tsx`

**Improvement #8 — SKU Catalogue Discrepancy:**

- [x] **G.5** Schema: Add `needs_clarification` to the documented status values in the status comment on the `orders` table. (No actual schema change needed — status is a TEXT field.)
  - File: `backend/app/schema.py` (comment only)

- [x] **G.6** Orchestrator: In `_handle_order_intent()`, after creating the order, check if any item has `matched_confidence < 0.7`. If so, set order status to `needs_clarification`. Generate a clarification message listing the uncertain items with alternatives from the product catalogue. Send via WhatsApp. Log to conversations and agent_actions.
  - File: `backend/app/orchestrator.py`

- [x] **G.7** Customer Agent: In the structured output, add an `unmatched_items` list (separate from `items`) for products the agent couldn't match at all. Each entry includes the original text and top 2–3 candidate matches with scores.
  - File: `backend/app/customer_agent.py`

- [x] **G.8** Router: Add `POST /api/orders/{id}/clarify` endpoint accepting `{ message: string }`. Sends the message to the customer via WhatsApp. Keeps order in `needs_clarification` status until the customer replies and the agent resolves the ambiguity (handled by the normal inbound pipeline).
  - File: `backend/app/routers/orders.py`

- [x] **G.9** Frontend API: Add `clarifyOrder(orderId: string, message: string)`.
  - File: `frontend/src/lib/api.ts`

- [x] **G.10** Frontend Order Queue: Add "Needs Clarification" to the filter tabs. For orders in `needs_clarification` status, show a "Clarify" button alongside Approve/Reject. Also show which items are uncertain (highlight rows with `matched_confidence < 0.7` in amber). Clicking "Clarify" opens a text input pre-filled with a suggested clarification message, editable before sending.
  - File: `frontend/src/app/orders/page.tsx`

- [x] **G.11** Typecheck: Run `npx tsc --noEmit`.

---

### Phase H: Bidirectional WhatsApp Logging (#11)
> Goal: Ensure all outbound messages are consistently logged with source tags. When the wholesaler sends a manual message, detect order-relevant changes and offer to apply them.

**Part A — Consistent outbound logging:**

- [x] **H.1** Schema: Add `source TEXT NOT NULL DEFAULT 'system'` column to `conversations` table. Values: `system` (auto-generated), `manual` (wholesaler-typed).
  - File: `backend/app/schema.py`

- [x] **H.2** CRUD: Update `save_conversation()` to accept an optional `source` parameter (default `"system"`). Pass it through to the INSERT.
  - File: `backend/app/crud.py`

- [x] **H.3** Audit outbound logging: Review every call to `send_whatsapp_message()` across the codebase and ensure a `save_conversation()` call follows. Specifically check:
  - `orchestrator.py`: `approve_order`, `reject_order`, `fulfil_order`, `_handle_remind_intent`, `_handle_general_intent`, `_handle_modify_intent`, `substitute_item`, `send_manual_message` → all should log with `source="system"` except `send_manual_message` which uses `source="manual"`
  - `nudge_scheduler.py`: `run_nudge_scan` → ensure nudge messages are logged with `source="system"`
  - File: `backend/app/orchestrator.py`, `backend/app/nudge_scheduler.py`

- [x] **H.4** Frontend types: Add `source: "system" | "manual"` to `Conversation` type.
  - File: `frontend/src/lib/types.ts`

- [x] **H.5** Frontend Conversation Timeline: Display a subtle "auto" tag on system-generated outbound messages. Manual messages show as normal outbound messages without the tag. This visually distinguishes "the system sent this" from "the wholesaler typed this".
  - File: `frontend/src/app/customers/[id]/page.tsx`

**Part B — Order-aware outbound analysis:**

- [x] **H.6** Customer Agent: Add `analyse_outbound_message(customer_id, message_text, pending_orders)` function. Uses the Claude API in a lightweight mode — system prompt asks: "A wholesaler sent this message to a customer. Does it imply any changes to the customer's pending orders? If so, return the changes as structured JSON." Returns a list of `DetectedOrderChange` objects or an empty list.
  - File: `backend/app/customer_agent.py`

- [x] **H.7** Orchestrator: Update `send_manual_message()` to call `analyse_outbound_message()` after sending. Return the detected changes in the response dict.
  - File: `backend/app/orchestrator.py`

- [x] **H.8** Router: Update `POST /api/orders/{id}/message` and `POST /api/customers/{id}/message` response format to include `detected_changes: list[dict]` in the JSON response. Each change has: `order_id`, `action` (add/remove/change_quantity), `product_id`, `product_name`, `quantity_change`, `confidence`.
  - File: `backend/app/routers/orders.py`, `backend/app/routers/customers.py`

- [x] **H.9** Frontend types: Add `DetectedOrderChange` interface: `{ order_id: string, action: string, product_id: string, product_name: string, quantity_change: number, confidence: number }`. Update `sendOrderMessage` and `sendCustomerMessage` return types to include `detected_changes`.
  - File: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`

- [x] **H.10** Frontend Order Queue: After `sendOrderMessage()` returns, check if `detected_changes` is non-empty. If so, show a confirmation modal/banner: "Detected order change: [description]. Apply this change?" with "Apply" and "Dismiss" buttons. "Apply" calls `updateOrderItems()` (from Phase E). "Dismiss" does nothing.
  - File: `frontend/src/app/orders/page.tsx`

- [x] **H.11** Frontend Customer Detail: Same logic as H.10 but for `sendCustomerMessage()`. If changes are detected, show the confirmation prompt with the relevant order ID linked.
  - File: `frontend/src/app/customers/[id]/page.tsx`

- [x] **H.12** Typecheck and E2E test: Run `npx tsc --noEmit`. Test the full flow: send a manual message that implies an order change → confirm the detection prompt appears → click Apply → verify the order was updated.

---

### Phase Summary & Dependencies

```
Phase A: Fulfilment Differential (#2) ─────────────────────┐
                                                            │
Phase B: Full Units (#7) + Flagged (#4) ───────────────────┤  (parallel with A)
                                                            │
Phase C: Message API (#6) ─────────────────────────────────┤  (parallel, needs credentials)
                                                            │
           ┌────────────────────────────────────────────────┘
           │ (A, B, C should complete before D)
           ▼
Phase D: Demand Overview (#5) + Manual Response (#3) ──────┐
                                                            │
           ┌────────────────────────────────────────────────┘
           │ (D must complete before E)
           ▼
Phase E: Manual Override (#9) ─────────────────────────────┐
                                                            │
           ┌────────────────────────────────────────────────┘
           │ (E should complete before F, G, H)
           ▼
Phase F: Health Score (#1) ─────────────────────────────────┐  (parallel with G)
                                                            │
Phase G: Multi-Channel (#10) + SKU Clarification (#8) ─────┤  (parallel with F)
                                                            │
           ┌────────────────────────────────────────────────┘
           │ (F + G should complete before H)
           ▼
Phase H: Bidirectional WhatsApp Logging (#11)
```

**Parallelisation opportunities:**
- Phases A, B, and C can be worked on simultaneously by different team members
- Phases F and G can be worked on simultaneously
- Each phase's backend and frontend tasks can be split between team members

**Total task count:** 78 tasks across 8 phases
