# Improvement Notes V2 — Response & Implementation Plan

This document addresses all 13 feedback items from `improvement_notes_v2.md`. For each item we diagnose the current behaviour, identify every affected file, and propose a concrete implementation approach.

---

## 1. Message Handling Improvements

### Current behaviour
The Customer Agent classifies messages into 5 intents: `place_order`, `repeat_order`, `modify_order`, `remind_last_order`, `general_inquiry`. When the LLM is available, it uses Claude with tool-use and confidence scores. When unavailable, a keyword-based fallback parser runs. The fallback parser produces low confidence scores (0.5–0.7) and adds anomaly flags.

**Issues identified against the feedback:**

- **1.1 — Unclear order-related messages**: Currently, low-confidence matches trigger `needs_clarification` status, which has its own tab. But the feedback wants these in the **Flagged** tab, with the ability to respond and have the message reclassified. The current system does auto-send a clarification message to the customer, but there's no structured reclassification loop — the customer's reply just re-enters the normal pipeline.

- **1.2 — Non-order messages**: Currently, `general_inquiry` intent triggers an auto-response ("Thank you for your message...") and logs to conversations. But it does **not** create an alert in the sidebar panel. The wholesaler only sees these in the customer's conversation history — they're not surfaced proactively.

- **1.3 — "The usual" / recurring orders**: Currently, `repeat_order` intent populates the order from the customer's `typical_basket` in their context. But no confirmation is sent to the customer asking "Did you mean XYZ?" — the order is created directly as `pending_confirmation` and the wholesaler approves/rejects. The customer never gets a chance to verify the interpretation before it reaches the wholesaler.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/orchestrator.py` | 1.1: Route low-confidence orders to `flagged` instead of `needs_clarification`. 1.2: Create an alert for `general_inquiry` messages. 1.3: For `repeat_order`, send a confirmation-of-interpretation message to the customer before creating the pending order. |
| `backend/app/customer_agent.py` | 1.3: Add a `confirm_interpretation` response text for repeat orders that lists what the system thinks "the usual" means. |
| `backend/app/crud.py` | Minor — may need a new alert type `"incoming_message"` for non-order messages. |
| `frontend/src/app/orders/page.tsx` | 1.1: Remove "Clarification" tab (covered in item #2). Show reclassification options on flagged orders. |
| `frontend/src/app/alerts/page.tsx` | 1.2: Show non-order message alerts with action button to open the customer's conversation view. |

### Proposed approach

**1.1 — Unclear orders → Flagged tab:**
- In `orchestrator.py`, change the low-confidence path: instead of `status = "needs_clarification"`, use `status = "flagged"` with a flag like `"Unclear order: items need verification"`. The clarification message is still sent to the customer automatically. When the customer replies, the agent re-parses and the order is either promoted to `pending_confirmation` (if clear) or stays `flagged` (if still unclear).
- On the frontend, flagged orders with a clarification flag show a "Clarify" button (already built) plus a new "Reclassify" dropdown: "This is an order" / "This is not an order" / "Still unclear". Selecting "not an order" moves the order to `rejected` with a note; "this is an order" moves it to `pending_confirmation`.

**1.2 — Non-order messages → Alert:**
- In `orchestrator._handle_general_intent()`, after sending the auto-response, create an alert of type `"incoming_message"` with detail: "Non-order message from [Customer]: [preview]". This surfaces the message in the Alerts sidebar.
- On the alerts page, `incoming_message` type alerts show a "Reply" button that opens the customer's conversation view (link to `/customers/{id}`).
- Add a set of pre-written quick-reply templates (e.g., "Thank you, we'll get back to you.", "Our delivery hours are 6am–2pm.", "Please contact us at [phone].") accessible from the alert.

**1.3 — Confirm "the usual":**
- For `repeat_order` intent, before creating the order, the orchestrator sends a WhatsApp message: "Can I confirm that by 'the usual' you mean: 20kg Chicken Breast, 10kg Potatoes, 5L Olive Oil? Reply 'Yes' to confirm or send corrections."
- The order is created with status `flagged` and a flag `"Awaiting customer confirmation of repeat order interpretation"`.
- When the customer replies "Yes", the Customer Agent classifies it as a confirmation → status moves to `pending_confirmation`. If they send corrections, the agent processes as `modify_order`.

### Complexity: Medium

---

## 2. Order Queue Adjustment — Delete Clarification Tab

### Current behaviour
The Order Queue has 7 tabs: Pending, Flagged, Clarification, Confirmed, Fulfilled, Rejected, All. The `needs_clarification` status is used when items have low confidence. This creates confusion about when to check Flagged vs Clarification.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/orchestrator.py` | Stop using `needs_clarification` status — use `flagged` with descriptive flags instead |
| `backend/app/crud.py` | Remove `needs_clarification` from `get_orders_overview()` counts; add its count into `flagged` |
| `frontend/src/app/orders/page.tsx` | Remove the "Clarification" tab from the filters array. Remove the "Approve Anyway" button specific to `needs_clarification`. |
| `frontend/src/app/page.tsx` | Remove `needs_clarification_count` from KPI display |
| `frontend/src/lib/types.ts` | Remove `needs_clarification_count` from `OrdersOverview` |
| `backend/app/schema.py` | Update status comment (cosmetic) |

### Proposed approach
- Merge `needs_clarification` into `flagged`. Every order that would have been `needs_clarification` now becomes `flagged` with an explicit flag string explaining why (e.g., "Low confidence match: 'the green stuff' matched to Spinach (62%)").
- The Clarify button remains on flagged orders — it just lives in the Flagged tab now.
- Remove the tab from the frontend filter list.
- Update `get_orders_overview()` to no longer count `needs_clarification` separately.

### Complexity: Low

---

## 3. Customer Sidebar Panel Improvements

### Current behaviour
The customer list page is a static 3-column grid of cards. No search, no sorting, no filtering, no view toggle. All customers are displayed in alphabetical order.

### Affected files
| File | What needs to change |
|------|---------------------|
| `frontend/src/app/customers/page.tsx` | Add search bar, sort dropdown, filter dropdown, view toggle (tile/list) |
| `frontend/src/lib/api.ts` | No backend change needed — filtering/sorting can be done client-side since we have ≤20 customers |

### Proposed approach

1. **Search bar**: Text input at the top. Filters customers client-side by `name` containing the search string (case-insensitive).

2. **Sort options**: Dropdown with options:
   - Name (A–Z) — default
   - Name (Z–A)
   - Health score (low → high) — surfaces at-risk customers first
   - Health score (high → low)
   - Pending order count (requires a small addition — count pending orders per customer)

3. **Filter options**: Multi-select or dropdown:
   - "Has pending orders"
   - "Has confirmed orders"
   - "At risk (health < 0.8)"
   - "All" (default)
   - This requires knowing each customer's order status counts. We can either fetch this from a new endpoint or compute it from the orders list.

4. **View toggle**: Two buttons (grid icon / list icon). Grid view shows the current card layout. List view shows a compact table row per customer: Name, Type, Health Score, Phone, Latest Event, with the same click-through to detail.

**Backend change needed**: Add `GET /api/customers/summary` that returns each customer with their pending/confirmed/fulfilled order counts, so the frontend can filter by order state. Alternatively, enrich the existing `GET /api/customers` endpoint with these counts.

### Complexity: Medium

---

## 4. Product Catalog Sidebar Panel

### Current behaviour
Products exist in the database and are searchable via `GET /api/products/search?q=...`, but there is no dedicated page to browse, add, edit, or delete products. The product list is only visible indirectly when editing an order.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/routers/products.py` | Add `POST /api/products` (create), `PUT /api/products/{id}` (update price/name), `DELETE /api/products/{id}` (delete) |
| `backend/app/crud.py` | Add `create_product()`, `update_product()`, `delete_product()` functions |
| `frontend/src/components/Sidebar.tsx` | Add "Product Catalog" nav item |
| New file: `frontend/src/app/catalog/page.tsx` | New page listing all products with add/edit/delete controls |
| `frontend/src/lib/api.ts` | Add `createProduct()`, `updateProduct()`, `deleteProduct()` calls |
| `frontend/src/lib/types.ts` | `Product` type already exists — may need `CreateProductInput` |

### Proposed approach

1. **New sidebar page "Product Catalog"** at route `/catalog`:
   - Table listing all products: Name, SKU, Category, Unit, Unit Type, Price
   - Search bar to filter by name/SKU
   - Category filter dropdown
   - "Add Product" button at top → inline form or modal with fields: Name, SKU, Category, Unit (dropdown: kg/L/pc/bottle/etc.), Price
   - Each row has an "Edit" button (inline price/name editing) and a "Delete" button (with confirmation)

2. **Backend CRUD**:
   - `POST /api/products`: Creates product with auto-generated ID, validates SKU uniqueness
   - `PUT /api/products/{id}`: Updates name, price_default (the mutable fields). SKU and category are immutable after creation.
   - `DELETE /api/products/{id}`: Soft-delete or hard-delete. Hard-delete only if no order_items reference it; otherwise mark as inactive.

3. **Sidebar**: Add nav item `{ href: "/catalog", label: "Product Catalog", icon: "▦" }`.

### Complexity: Medium

---

## 5. Intelligent Manual Messaging

### Current behaviour
Manual message inputs exist on the order detail view and customer detail page. They are plain text inputs — the wholesaler types freely. No suggestions, no pre-filled text, no templates.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/orchestrator.py` | Add `generate_suggested_messages(customer_id, context_type)` that uses the LLM to produce 2–3 contextual message suggestions |
| `backend/app/routers/orders.py` | Add `GET /api/orders/{id}/suggestions` endpoint |
| `backend/app/routers/customers.py` | Add `GET /api/customers/{id}/suggestions` endpoint |
| `frontend/src/app/orders/page.tsx` | Show suggestion chips above the message input; clicking one fills the input |
| `frontend/src/app/customers/[id]/page.tsx` | Same suggestion chips above the customer-level message input |
| `frontend/src/lib/api.ts` | Add `getMessageSuggestions(orderId)` and `getCustomerMessageSuggestions(customerId)` |

### Proposed approach

1. **Backend**: A new function `generate_suggested_messages(customer_id, order_id=None)` that:
   - Loads the customer context, recent conversations, and (if provided) the order details
   - Calls Claude with a short prompt: "Generate 3 short suggested WhatsApp messages a wholesaler might send to this customer given this context. Keep them professional, concise, and actionable."
   - Returns a list of 2–3 message strings
   - Falls back to static templates if LLM is unavailable:
     - For orders: "Your order has been received and is being reviewed.", "We need to adjust an item on your order — details to follow.", "Your order is ready for dispatch."
     - For general: "Thank you for your message, we'll get back to you shortly.", "Our delivery hours are 6am–2pm Monday–Saturday.", "Please let us know if you'd like to place an order."

2. **Frontend**: Above each message input, show the suggestions as clickable chips/buttons. Clicking one fills the text input (user can still edit before sending). Suggestions load when the expanded order view or customer detail opens.

3. **On alerts** (item 1.2): Non-order message alerts also show quick-reply suggestion chips.

### Complexity: Medium

---

## 6. Activity Log Improvements

### Current behaviour
The Activity Log displays an "Entity" column formatted as `{entity_type}/{entity_id_first_12_chars}` — e.g., `customer/cust-002` or `order/ord-339e2`. This is opaque. The user wants to see the customer name and/or order number instead.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/crud.py` | Update `get_agent_actions()` to JOIN on customers/orders tables and return `customer_name` and `order_id` alongside the raw entity data |
| `frontend/src/app/activity/page.tsx` | Replace the entity column with two columns: "Customer" and "Order". Show the name/ID if applicable, leave blank if not. |
| `frontend/src/lib/types.ts` | Add `customer_name: string | null` and `related_order_id: string | null` to `AgentAction` |

### Proposed approach

1. **Backend**: Modify `get_agent_actions()` to do a LEFT JOIN:
   - If `entity_type = 'customer'`, join `customers` to get `name`
   - If `entity_type = 'order'`, join `orders` to get the `customer_id`, then join `customers` to get the customer name. Also return the order ID.
   - For `entity_type = 'phone'` (unknown customer), show the phone number in the customer column.

2. **Frontend**: Replace the single "Entity" column with:
   - **Customer**: Shows customer name (clickable link to `/customers/{id}`), or phone number for unknown customers, or "—" if not applicable
   - **Order**: Shows order ID (clickable link or expandable), or "—" if not applicable

3. Parse `details_json` to extract `order_id` when entity_type is `customer` (some actions on customers are order-related and store the order_id in details).

### Complexity: Low

---

## 7. Nudge Trigger Scan Redesign

### Current behaviour
The nudge scheduler is fully automatic — when `POST /api/nudge/run` is called (or on a cron schedule), it immediately sends WhatsApp nudge messages to all overdue customers. The wholesaler has no opportunity to review, edit, or suppress nudges before they go out.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/nudge_scheduler.py` | Change from auto-send to creating "nudge suggestions" that the wholesaler reviews. Don't send WhatsApp messages directly. |
| `backend/app/crud.py` | Add a `nudge_suggestions` table or reuse alerts with a new type `"nudge_suggestion"` |
| `backend/app/schema.py` | Possibly add a `nudge_suggestions` table: `(id, customer_id, suggested_message, reason, status, created_at)` |
| `backend/app/routers/nudge.py` | Add `GET /api/nudge/suggestions` and `POST /api/nudge/suggestions/{id}/send` (approve and send) and `POST /api/nudge/suggestions/{id}/dismiss` |
| `frontend/src/app/customers/page.tsx` | Highlight customers who have pending nudge suggestions. In tile view, show a "Send Nudge" shortcut button. |
| `frontend/src/app/customers/[id]/page.tsx` | In the customer detail view, show pending nudge suggestions with the suggested message, reason, and option to edit/send/dismiss. |
| `frontend/src/lib/types.ts` | Add `NudgeSuggestion` type |
| `frontend/src/lib/api.ts` | Add `getNudgeSuggestions()`, `sendNudge(id)`, `dismissNudge(id)`, `sendCustomNudge(customerId, message)` |

### Proposed approach

1. **Change the nudge scan from "auto-send" to "suggest"**: When `run_nudge_scan()` detects overdue customers, instead of calling `send_whatsapp_message()`, it creates a `nudge_suggestion` record with the suggested message text, the reason ("3 days overdue on usual Tuesday order"), and status `pending`.

2. **Customer list integration**: Customers with pending nudge suggestions get a visual indicator (e.g., a small bell icon or "Nudge suggested" badge on their card). In tile view, a "Send Nudge" shortcut button appears.

3. **Customer detail integration**: Pending nudge suggestions appear as a callout below the health timeline. Show the suggested message (pre-filled, editable), the reason, and three buttons: "Send as-is", "Edit & Send", "Dismiss".

4. **Backend endpoints**:
   - `GET /api/nudge/suggestions` — list pending suggestions
   - `POST /api/nudge/suggestions/{id}/send` — approve and send (optionally with custom message override)
   - `POST /api/nudge/suggestions/{id}/dismiss` — mark as dismissed
   - The existing `POST /api/nudge/run` now creates suggestions instead of sending messages

5. **Churn alerts remain automatic** — only the nudge messages get the approval gate. High-risk churn alerts still appear in the Alerts panel immediately.

### Complexity: Medium

---

## 8. Dashboard Interactivity Improvements

### Current behaviour
The overview dashboard shows KPI cards, recent orders, and active alerts. None of these are interactive — KPI cards are static displays, order rows are not clickable, and alerts have no action buttons.

### Affected files
| File | What needs to change |
|------|---------------------|
| `frontend/src/app/page.tsx` | Make KPI cards clickable (link to filtered Order Queue). Make order rows clickable (link to order detail). Add action buttons on alerts. |

### Proposed approach

1. **KPI cards → clickable links**:
   - "Pending" card → links to `/orders?filter=pending_confirmation`
   - "Confirmed" card → links to `/orders?filter=confirmed`
   - "Fulfilled Today" card → links to `/orders?filter=fulfilled`
   - "Flagged / Rejected" card → links to `/orders?filter=flagged`
   - Use Next.js `Link` wrapper around each `KpiCard`, or make `KpiCard` accept an `href` prop.

2. **Recent orders → clickable rows**:
   - Each order row links to `/orders?expanded={order_id}` or more simply opens the Order Queue page with that order expanded.
   - Alternative approach: clicking an order row navigates to `/orders` with the status filter set and auto-expands that order. This requires the Order Queue page to accept a URL query param for auto-expansion.

3. **Active alerts → action buttons**:
   - Each alert type gets a contextual action:
     - `anomaly` / `agent_note` → "Review Order" button → navigates to `/orders` with Flagged tab
     - `churn_risk` → "View Customer" button → navigates to `/customers/{id}`
     - `incoming_message` → "Reply" button → navigates to `/customers/{id}`
     - `order_modified` → "Review Order" → navigates to `/orders` with Pending tab
   - Show as a small button/link at the end of each alert row.

### Complexity: Low

---

## 9. More Agentic User Experience

### Current behaviour
All user feedback is inline status text (e.g., "Sent!", "Order confirmed") in muted grey. No toast/popup notifications. No conversation-state indicators. Language is functional but not agent-like.

### Affected files
| File | What needs to change |
|------|---------------------|
| New file: `frontend/src/components/Toast.tsx` | Create a toast notification system |
| `frontend/src/app/layout.tsx` | Add toast provider to the layout |
| `frontend/src/app/orders/page.tsx` | Replace inline status text with toast notifications. Add "Awaiting customer response" state indicator on orders. |
| `frontend/src/app/customers/[id]/page.tsx` | Add conversation state indicators |
| `frontend/src/app/page.tsx` | Adjust KPI card labels to be more action-oriented |
| Various | Update UI copy to be more agent-like throughout |

### Proposed approach

1. **Toast notification system**: Build a minimal toast component (no external library needed). Toasts appear in the top-right corner, auto-dismiss after 3 seconds, and support types: `success` (green), `info` (blue), `error` (red). Use React context for a global `showToast(message, type)` function.
   - Show toasts for: order approved, order fulfilled, message sent, nudge sent, alert dismissed, order edited.

2. **Conversation state indicators**: On the order detail and customer conversation view, show a subtle status line:
   - "Awaiting customer response" (when last message was outbound and there's a pending order or clarification)
   - "Customer responded — review needed" (when last message was inbound and there's a flagged/pending order)
   - Visual: small badge or italic text below the conversation thread.

3. **Agent-like language adjustments**:
   - "Approve" → "Confirm Order"
   - "Reject" → "Decline Order"
   - "Mark Fulfilled" → "Dispatch Order"
   - "Send" → "Send via WhatsApp"
   - KPI labels: "Pending" → "Awaiting Review", "Flagged" → "Needs Attention"
   - Add subtle agent status messages: "Agent processed 12 orders overnight" on the overview page.

4. **UI reorganisation** (lightweight): Add an "Agent Status" section at the top of the overview page showing the last agent activity timestamp and a one-liner like "Agent is active — 3 orders processed in the last hour."

### Complexity: Medium

---

## 10. Image Input Processing

### Current behaviour
When a customer sends an image via WhatsApp, the system downloads it, converts to base64, and passes it as `[IMAGE:{base64}]` to the Customer Agent. However, the Customer Agent's system prompt and LLM call do **not** use Claude's vision capability — the image is treated as a text string. The base64 data is passed as part of the text message, which means Claude can't actually "see" the image.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/customer_agent.py` | When `message_type == "image"`, use Claude's multimodal API to pass the image as an `image` content block alongside the text. Update the system prompt to include image processing instructions. |
| `backend/app/whatsapp.py` | Return base64 data separately (not embedded in the text string) |
| `backend/app/pipeline.py` | Pass the image data separately to the Customer Agent |
| `backend/app/schema.py` | Add `image_url TEXT` column to `conversations` table to store image references |
| `backend/app/crud.py` | Update `save_conversation()` to accept an optional `image_data` parameter |
| `frontend/src/app/customers/[id]/page.tsx` | Display images inline in the conversation timeline |
| `frontend/src/lib/types.ts` | Add `image_url: string | null` to `Conversation` |
| Data storage | Save images to disk (e.g., `data/images/`) and store the path in the DB |

### Proposed approach

1. **Backend — proper multimodal processing**:
   - In `whatsapp.py`, `process_incoming_message()` returns a tuple `(text, image_base64)` instead of a single string with `[IMAGE:...]` prefix.
   - In `pipeline.py`, pass both text and image data to the Customer Agent.
   - In `customer_agent.py`, when image data is present, construct the Claude API call with a multimodal content block:
     ```python
     messages = [{"role": "user", "content": [
         {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
         {"type": "text", "text": user_message}
     ]}]
     ```
   - Update the system prompt to include: "If an image is provided, examine it for handwritten or printed order items. Extract product names, quantities, and any other order-relevant information."

2. **Image storage**: Save images to `data/images/{customer_id}/{timestamp}.jpg`. Store the file path in a new `image_url` column on `conversations`.

3. **Frontend**: In the conversation timeline, if `image_url` is set, display a small thumbnail of the image alongside the message text. Clicking the thumbnail opens it full-size.

4. **Order history reflection**: When an order is created from an image-based message, the `raw_message` field stores the extracted text and the `image_url` is linked through the conversation record.
# Edit: Here again, please confirm the order with the customers, similar to how you did it with the recurring order phrsing (e.g., "the usual") in 1.1.3

### Complexity: Medium–High

---

## 11. WhatsApp Customer Integration — Real Customer Profiles

### Current behaviour
The system has 15 seeded demo customers with German phone numbers (`+49176...`). The two real WhatsApp numbers (`+44 7460 880940` for Mantas and `+1 (812) 801-7698` for Ben) are not in the system, so messages from them would trigger the "unknown customer" alert and not be processed.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/seed.py` | Add two new customer entries with real phone numbers and basic context |

### Proposed approach

Add two new customers to the `CUSTOMERS` list in `seed.py`:

```python
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
        ("MEAT-001", 10),  # Chicken Breast
        ("PROD-001", 5),   # Potatoes
        ("DRY-001", 3),    # Olive Oil
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
        ("MEAT-001", 15),  # Chicken Breast
        ("PROD-004", 5),   # Tomatoes
        ("DRY-005", 2),    # Pasta
    ],
},
```

These customers will get context files, order patterns, and be recognisable by the system when they send WhatsApp messages. No historical orders are seeded (they're new), so the agent will rely on the typical basket for "the usual" type orders.

### Complexity: Low

---

## 12. Automatic Customer Profile Creation

### Current behaviour
When an unknown phone number sends a message, `pipeline.py` creates an alert of type `"unknown_customer"` and returns without processing. The message is effectively dropped after the alert. There is no mechanism to create a new customer profile from an incoming message.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/pipeline.py` | Instead of just alerting, auto-create a minimal customer profile from the incoming message |
| `backend/app/crud.py` | Add `create_customer(name, phone, ...)` function |
| `backend/app/customer_agent.py` | Add a mode to extract customer name/info from a first-contact message |
| `backend/app/orchestrator.py` | Add `send_welcome_message(customer_id)` function |
| `backend/app/routers/customers.py` | Add `POST /api/customers` for manual customer creation from the dashboard |
| `frontend/src/app/alerts/page.tsx` | For `unknown_customer` alerts (which now show the auto-created profile), add "View Customer" action |

### Proposed approach

1. **Auto-create on first message**: When `get_customer_by_phone()` returns `None`:
   - Create a new customer record with:
     - `id`: auto-generated (`cust-{uuid}`)
     - `name`: extracted from the message if possible (e.g., "Hi, I'm Chef Marco..."), otherwise "New Customer ({phone})"
     - `type`: "unknown" (to be updated later)
     - `contact_phone` / `contact_whatsapp`: the sender's phone number
     - `delivery_address`: "Not provided"
     - `health_score`: 1.0
   - Create an empty `customer_context` record
   - Create an alert: "New customer profile created for {phone}. Please review and update details."

2. **Welcome message**: After creating the profile, send a welcome WhatsApp message: "Welcome! We've set up your account. Please let us know your name and delivery address, and we'll be happy to take your orders."

3. **Process the original message**: After creating the profile, continue processing the message through the normal pipeline (Customer Agent → Orchestrator). This means first-contact messages that contain orders will be parsed and appear on the dashboard.

4. **Manual creation from dashboard**: Add a "Add Customer" button on the customer list page that opens a form. This covers cases where the wholesaler wants to pre-create a profile before the customer messages.

### Complexity: Medium

---

## 13. Background App Refresh & Multi-Threading

### Current behaviour

**Refresh**: The frontend polls every 5 seconds (`setInterval(loadData, 5000)`) on most pages. This means changes do appear without manual refresh, but with up to 5 seconds of latency. However, the user reports needing to "refresh the app" — this suggests either the polling is not working reliably, or certain state changes (like a newly created order from an image upload) don't trigger a re-render because the processing takes longer than expected.

**Multi-threading / Concurrency**: The FastAPI backend uses `uvicorn` which runs on Python's asyncio event loop. While the endpoints are declared `async`, several critical operations are **blocking**:
- **SQLite calls**: All database access uses the synchronous `sqlite3` module. Every query blocks the event loop.
- **Anthropic API calls**: `client.messages.create()` is a synchronous call that blocks the event loop until Claude responds (can be 2–10 seconds).
- **Result**: While one request is being processed (e.g., image → transcribe → Claude → DB write), the entire event loop is blocked. Other requests (including the frontend's 5-second polls) must wait.

### Affected files
| File | What needs to change |
|------|---------------------|
| `backend/app/customer_agent.py` | Switch from synchronous `client.messages.create()` to async `client.messages.create()` using `anthropic.AsyncAnthropic` |
| `backend/app/database.py` | Wrap synchronous SQLite calls in `asyncio.to_thread()` to avoid blocking the event loop, OR switch to `aiosqlite` |
| `backend/app/crud.py` | If switching to `aiosqlite`, make all CRUD functions async. If using `to_thread`, wrap at the database.py level. |
| `backend/app/pipeline.py` | Ensure the webhook handler returns immediately and processes the message in a background task |
| `backend/app/main.py` | Add `BackgroundTasks` from FastAPI for long-running operations |
| `backend/app/routers/webhook.py` | Use FastAPI's `BackgroundTasks` to process messages without blocking the webhook response |
| `frontend/src/app/page.tsx` | Reduce poll interval or add WebSocket for real-time updates |
| `backend/requirements.txt` | Add `aiosqlite` if switching to async DB |

### Proposed approach

**Approach A — Pragmatic (recommended for hackathon):**

1. **Non-blocking webhook**: The most impactful change. Currently the webhook handler processes the entire pipeline (download media → transcribe → Claude → DB) synchronously before returning `200 OK` to Meta. This means Meta's webhook times out if processing takes too long, AND the event loop is blocked for other requests.
   - Solution: Use FastAPI's `BackgroundTasks` to offload message processing:
   ```python
   @router.post("")
   async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
       payload = await request.json()
       messages = parse_webhook_payload(payload)
       for msg in messages:
           background_tasks.add_task(process_and_handle, msg)
       return {"status": "ok"}
   ```
   - This returns `200 OK` immediately to Meta, then processes in the background.

2. **Async Anthropic client**: Switch from `anthropic.Anthropic` to `anthropic.AsyncAnthropic` and use `await client.messages.create()`. This is a small change that yields major concurrency benefits — multiple Claude calls can run in parallel.

3. **SQLite via `asyncio.to_thread()`**: Wrap the `get_db()` context manager calls in `asyncio.to_thread()` at the router level. This is simpler than switching to `aiosqlite` — it pushes blocking DB calls to a thread pool, freeing the event loop:
   ```python
   result = await asyncio.to_thread(get_customer_by_phone, phone)
   ```
   However, this requires making the CRUD layer async-aware, which is pervasive. A simpler middle ground: just wrap the long-running pipeline function in `to_thread`.

4. **Frontend**: The 5-second polling already exists and works. The real fix is ensuring the backend doesn't block during processing. Once the webhook is non-blocking, poll responses will be instant.

**Approach B — Production-grade (future):**
- Switch to `aiosqlite` or PostgreSQL with `asyncpg`
- Add WebSocket endpoint for real-time push updates (no polling needed)
- Use Celery or similar task queue for LLM processing

**Recommendation**: Implement Approach A — it's 90% of the benefit with minimal code change. The key insight is: the webhook must return immediately, and the Anthropic client must be async. Everything else is secondary.
# Edit: Please use Approach A.

### Complexity: Medium

---

## Summary: Priority & Dependency Map

| # | Improvement | Complexity | Dependencies |
|---|------------|-----------|--------------|
| 2 | Delete Clarification Tab | Low | None — do first, simplifies the order queue |
| 11 | Real Customer Profiles | Low | None — just seed data |
| 6 | Activity Log Improvements | Low | None |
| 8 | Dashboard Interactivity | Low | None |
| 13 | Background Refresh & Multi-Threading | Med | None — critical infrastructure fix |
| 1 | Message Handling Improvements | Med | #2 (merged clarification into flagged) |
| 3 | Customer Panel Improvements | Med | None |
| 4 | Product Catalog | Med | None |
| 7 | Nudge Trigger Redesign | Med | None |
| 9 | Agentic UX | Med | None, but benefits from all other items |
| 5 | Intelligent Manual Messaging | Med | #1 (needs message context) |
| 12 | Auto Customer Profile Creation | Med | #11 (patterns from real profiles) |
| 10 | Image Input Processing | Med–High | #13 (needs non-blocking processing) |

### Recommended implementation order

1. **#2 Delete Clarification Tab** + **#11 Real Customer Profiles** — quick wins, clean up the UI
2. **#13 Background Refresh & Multi-Threading** — critical infrastructure, unblocks #10
3. **#6 Activity Log** + **#8 Dashboard Interactivity** — low-effort UX improvements
4. **#1 Message Handling** + **#7 Nudge Redesign** — core agent behaviour improvements
5. **#3 Customer Panel** + **#4 Product Catalog** — new sidebar features
6. **#9 Agentic UX** + **#5 Intelligent Messaging** — polish and intelligence layer
7. **#12 Auto Customer Creation** + **#10 Image Processing** — advanced features, build last

---
---

## Detailed Implementation Todo List

Organised into 7 phases following the recommended implementation order.

---

### Phase A: Quick Wins — Clarification Tab Removal (#2) + Real Customers (#11)

- [ ] **A.1** Backend: In `orchestrator.py`, replace all uses of `status = "needs_clarification"` with `status = "flagged"` plus a descriptive flag string (e.g., "Low confidence match: items need verification").
- [ ] **A.2** Backend: In `crud.py`, remove `needs_clarification_count` from `get_orders_overview()`. Merge its count into `flagged_count`.
- [ ] **A.3** Frontend types: Remove `needs_clarification_count` from `OrdersOverview` in `types.ts`.
- [ ] **A.4** Frontend orders page: Remove the `{ value: "needs_clarification", label: "Clarification" }` entry from the filters array. Remove the "Approve Anyway" button block for `needs_clarification`. The Clarify button stays on flagged orders.
- [ ] **A.5** Frontend overview: Remove `needs_clarification_count` reference from the KPI card subtitle.
- [ ] **A.6** Seed: Add Mantas (`+447460880940`) and Ben (`+18128017698`) as customers in `seed.py` with basic baskets and context.
- [ ] **A.7** Re-seed database and typecheck.

---

### Phase B: Infrastructure — Background Processing (#13)

- [ ] **B.1** Backend: In `customer_agent.py`, switch from `anthropic.Anthropic` to `anthropic.AsyncAnthropic`. Change `client.messages.create()` to `await client.messages.create()`. Make `run_customer_agent` and `analyse_outbound_message` properly async.
- [ ] **B.2** Backend: In `routers/webhook.py`, use FastAPI `BackgroundTasks` to offload `process_and_handle` so the webhook returns `200 OK` immediately.
- [ ] **B.3** Backend: In `pipeline.py`, wrap the blocking `run_customer_agent()` and `handle_agent_output()` calls to work with the async Anthropic client.
- [ ] **B.4** Backend: In `routers/simulate.py`, apply the same background task pattern for the simulation endpoint.
- [ ] **B.5** Frontend: Verify the 5-second polling works correctly now that the backend doesn't block. Consider reducing poll interval to 3 seconds on the overview and order queue pages.
- [ ] **B.6** Typecheck and test.

---

### Phase C: UX Quick Wins — Activity Log (#6) + Dashboard (#8)

**Activity Log (#6):**

- [ ] **C.1** Backend: Update `get_agent_actions()` in `crud.py` to LEFT JOIN on `customers` and `orders` tables. Return `customer_name` and `related_order_id` in addition to raw `entity_type`/`entity_id`. For `entity_type='order'`, also resolve the customer name through the order.
- [ ] **C.2** Frontend types: Add `customer_name: string | null` and `related_order_id: string | null` to `AgentAction`.
- [ ] **C.3** Frontend activity page: Replace the "Entity" column with "Customer" and "Order" columns. Customer column shows the name (linked to `/customers/{id}`) or "—". Order column shows the order ID or "—".

**Dashboard Interactivity (#8):**

- [ ] **C.4** Frontend overview: Make `KpiCard` accept an optional `href` prop. Wrap the card in a `Link` when `href` is provided. Map: Pending → `/orders`, Confirmed → `/orders`, Fulfilled → `/orders`, Flagged → `/orders`.
- [ ] **C.5** Frontend overview: Make recent order rows clickable. Each row links to `/orders` (the order queue page). Store the filter value as a query param if needed.
- [ ] **C.6** Frontend overview: Add action buttons on alerts. Each alert type gets a contextual link: `anomaly`/`agent_note` → "Review" (link to `/orders`), `churn_risk` → "View" (link to `/customers/{id}`), `incoming_message` → "Reply" (link to `/customers/{id}`).
- [ ] **C.7** Typecheck.

---

### Phase D: Message Handling (#1) + Nudge Redesign (#7)

**Message Handling (#1):**

- [ ] **D.1** Backend: In `orchestrator._handle_general_intent()`, after sending the auto-response, create an alert of type `"incoming_message"` with detail including customer name and message preview. This surfaces non-order messages in the Alerts panel.
- [ ] **D.2** Backend: For `repeat_order` intent, before creating the order, send a WhatsApp confirmation: "Can I confirm that by 'the usual' you mean: [items list]? Reply 'Yes' to confirm or send corrections." Set order status to `flagged` with flag `"Awaiting customer confirmation of repeat order"`.
- [ ] **D.3** Frontend orders page: On flagged orders, add a "Reclassify" dropdown with options: "This is a valid order" (moves to `pending_confirmation`), "Not an order" (moves to `rejected`), "Still unclear" (keeps as `flagged`). This requires a new backend endpoint `POST /api/orders/{id}/reclassify` accepting `{ new_status: string }`.
- [ ] **D.4** Backend: Add `POST /api/orders/{id}/reclassify` endpoint.
- [ ] **D.5** Frontend API: Add `reclassifyOrder(orderId, newStatus)`.
- [ ] **D.6** Frontend alerts page: For `incoming_message` alerts, show a "Reply" button linking to the customer detail page.

**Nudge Redesign (#7):**

- [ ] **D.7** Backend schema: Add `nudge_suggestions` table: `(id TEXT PK, customer_id TEXT FK, suggested_message TEXT, reason TEXT, status TEXT DEFAULT 'pending', created_at TEXT)`.
- [ ] **D.8** Backend crud: Add `create_nudge_suggestion()`, `get_nudge_suggestions()`, `update_nudge_suggestion_status()`.
- [ ] **D.9** Backend nudge_scheduler: Change `run_nudge_scan()` to create nudge suggestions instead of sending messages directly. Only churn alerts remain automatic.
- [ ] **D.10** Backend router: Add `GET /api/nudge/suggestions`, `POST /api/nudge/suggestions/{id}/send` (sends the message and marks as sent), `POST /api/nudge/suggestions/{id}/dismiss`.
- [ ] **D.11** Frontend types: Add `NudgeSuggestion` type.
- [ ] **D.12** Frontend API: Add `getNudgeSuggestions()`, `sendNudge(id, customMessage?)`, `dismissNudge(id)`.
- [ ] **D.13** Frontend customers page: Show a nudge indicator on customer cards that have pending suggestions. Add a "Send Nudge" shortcut button.
- [ ] **D.14** Frontend customer detail: Show pending nudge suggestions below the health timeline with editable message, reason, and Send/Dismiss buttons.
- [ ] **D.15** Typecheck.

---

### Phase E: New Panels — Customer Panel (#3) + Product Catalog (#4)

**Customer Panel (#3):**

- [ ] **E.1** Backend: Enrich `GET /api/customers` response to include `pending_order_count`, `confirmed_order_count`, `fulfilled_order_count` per customer (subquery or JOIN).
- [ ] **E.2** Frontend customers page: Add search bar (filters client-side by name).
- [ ] **E.3** Frontend customers page: Add sort dropdown (Name A–Z, Name Z–A, Health low→high, Health high→low).
- [ ] **E.4** Frontend customers page: Add filter dropdown (All, Has pending orders, Has confirmed orders, At risk).
- [ ] **E.5** Frontend customers page: Add view toggle (tile / list). List view shows a compact table row per customer.
- [ ] **E.6** Frontend types: Add `pending_order_count`, `confirmed_order_count`, `fulfilled_order_count` to `Customer`.

**Product Catalog (#4):**

- [ ] **E.7** Backend crud: Add `create_product()`, `update_product()`, `delete_product()`.
- [ ] **E.8** Backend router: Add `POST /api/products`, `PUT /api/products/{id}`, `DELETE /api/products/{id}`.
- [ ] **E.9** Frontend sidebar: Add `{ href: "/catalog", label: "Product Catalog", icon: "▦" }`.
- [ ] **E.10** Frontend new page `catalog/page.tsx`: Table of all products with search, category filter, Add Product form, inline edit (price), delete button.
- [ ] **E.11** Frontend API: Add `createProduct()`, `updateProduct()`, `deleteProduct()`.
- [ ] **E.12** Frontend types: Add `CreateProductInput` type.
- [ ] **E.13** Typecheck.

---

### Phase F: Polish — Agentic UX (#9) + Intelligent Messaging (#5)

**Agentic UX (#9):**

- [ ] **F.1** Frontend: Create `components/Toast.tsx` — a toast notification component with React context provider. Supports success/info/error types. Auto-dismisses after 3 seconds.
- [ ] **F.2** Frontend layout: Wrap the app in `ToastProvider` in `layout.tsx`.
- [ ] **F.3** Frontend orders page: Replace inline status text with toast calls. Show toasts for: order confirmed, order dispatched, message sent, order edited.
- [ ] **F.4** Frontend customer detail: Show toasts for: message sent, note logged.
- [ ] **F.5** Frontend orders page: Add conversation state indicators on expanded orders. Show "Awaiting customer response" when last conversation was outbound and order is flagged/pending.
- [ ] **F.6** Frontend: Update UI copy throughout. "Approve" → "Confirm Order", "Reject" → "Decline Order", "Mark Fulfilled" → "Dispatch Order", "Send" → "Send via WhatsApp". KPI labels: "Pending" → "Awaiting Review".
- [ ] **F.7** Frontend overview: Add an "Agent Status" section showing last agent activity and a one-liner summary.

**Intelligent Messaging (#5):**

- [ ] **F.8** Backend: Add `generate_suggested_messages(customer_id, order_id=None)` in `orchestrator.py`. Uses Claude to generate 2–3 contextual message suggestions. Falls back to static templates.
- [ ] **F.9** Backend router: Add `GET /api/orders/{id}/suggestions` and `GET /api/customers/{id}/suggestions`.
- [ ] **F.10** Frontend API: Add `getMessageSuggestions(orderId)` and `getCustomerSuggestions(customerId)`.
- [ ] **F.11** Frontend orders page: Show suggestion chips above the message input when expanded. Clicking fills the input.
- [ ] **F.12** Frontend customer detail: Same suggestion chips above the customer-level message input.
- [ ] **F.13** Typecheck.

---

### Phase G: Advanced Features — Auto Customer Creation (#12) + Image Processing (#10)

**Auto Customer Creation (#12):**

- [ ] **G.1** Backend crud: Add `create_customer(name, phone, customer_type, address)` function. Auto-generates ID, creates empty context.
- [ ] **G.2** Backend pipeline: Replace the early-return for unknown phone numbers. Instead: auto-create customer profile, send welcome message, then continue processing the original message through the agent.
- [ ] **G.3** Backend orchestrator: Add `send_welcome_message(customer_id)` function.
- [ ] **G.4** Backend router customers: Add `POST /api/customers` for manual creation from the dashboard.
- [ ] **G.5** Frontend customers page: Add "Add Customer" button opening a creation form (name, phone, type, address).
- [ ] **G.6** Frontend API: Add `createCustomer(data)`.

**Image Processing (#10):**

- [ ] **G.7** Backend whatsapp: Refactor `process_incoming_message()` to return structured data `(text, image_base64)` instead of a single string.
- [ ] **G.8** Backend pipeline: Pass image data separately to `run_customer_agent()`.
- [ ] **G.9** Backend customer_agent: When image data is present, construct a multimodal Claude API call with `image` content block. Update the system prompt to include image-reading instructions.
- [ ] **G.10** Backend: Save images to `data/images/{customer_id}/` directory. Add `image_url` column to `conversations` table.
- [ ] **G.11** Backend crud: Update `save_conversation()` to accept optional `image_url`.
- [ ] **G.12** Backend: Add a static file serving route for images, or return base64 inline.
- [ ] **G.13** Frontend types: Add `image_url: string | null` to `Conversation`.
- [ ] **G.14** Frontend customer detail: Display image thumbnails inline in the conversation timeline. Clicking opens full-size.
- [ ] **G.15** Typecheck and E2E test with a real image.

---

### Phase Summary & Dependencies

```
Phase A: Quick Wins (#2, #11) ─────────────────────────────┐
                                                            │
Phase B: Infrastructure (#13) ─────────────────────────────┤  (parallel with A)
                                                            │
           ┌────────────────────────────────────────────────┘
           │ (A + B should complete before C)
           ▼
Phase C: UX Quick Wins (#6, #8) ───────────────────────────┐
                                                            │
           ┌────────────────────────────────────────────────┘
           ▼
Phase D: Message Handling (#1) + Nudge Redesign (#7) ──────┐
                                                            │
Phase E: Customer Panel (#3) + Product Catalog (#4) ───────┤  (parallel with D)
                                                            │
           ┌────────────────────────────────────────────────┘
           ▼
Phase F: Agentic UX (#9) + Intelligent Messaging (#5) ────┐
                                                            │
           ┌────────────────────────────────────────────────┘
           ▼
Phase G: Auto Customer Creation (#12) + Image Processing (#10)
```

**Parallelisation opportunities:**
- Phases A and B can run in parallel
- Phases D and E can run in parallel
- Backend and frontend tasks within each phase can be split between team members

**Total task count:** 80 tasks across 7 phases
