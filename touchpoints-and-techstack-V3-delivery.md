# Touchpoints & Tech Stack — V3 Delivery (Implementation Guide)

This document is the **implementation reference** for the hackathon build. It covers scope, architecture, tech stack, data model, and agent design — everything needed to write code.

---

## Part 1: Scope & Actors

### Actors

Two actors only. Suppliers are out of scope — **infinite stock assumed**.

```
┌─────────────────┐                    ┌──────────────────────┐
│   CUSTOMERS      │                    │   WHOLESALER          │
│                  │                    │                       │
│ • Restaurants    │◄──── WhatsApp ────►│ • Inside sales team   │
│ • Hotels         │                    │ • Field reps          │
│ • Caterers       │                    │ • Warehouse staff     │
│ • Small retail   │                    │ • Finance/credit      │
│ • Canteens       │                    │                       │
└─────────────────┘                    └──────────────────────┘
```

### Target Company Profile
- Up to 50 employees
- Mid-size regional wholesalers (revenue €20M–200M)
- Currently relying on phone, WhatsApp, email, fax for order intake
- No dedicated IT teams

### MVP Assumptions
- **Infinite stock** — no supplier or procurement logic
- **WhatsApp only** — single communication channel for customer interactions
- **Customers order the same items** — only quantity varies, not product type
- **English only** — all interfaces, messages, and examples

---

## Part 2: Features by Priority

### TIER 1 — Build at Hackathon

#### 1. Order Placement (WhatsApp Inbox)

**What it does:**
- Ingests orders from WhatsApp (text messages, voice notes via transcription, photos of handwritten lists)
- Parses unstructured natural language into structured order (product, quantity, unit, delivery date)
- Fuzzy-matches to product catalogue ("the usual cheese, but the big one" → Emmentaler 500g)
- Flags anomalies: "This customer usually orders 50 cases. They ordered 500. Confirm?"
- **Does NOT auto-confirm** — sends parsed order to wholesaler dashboard for approval
- After wholesaler confirms, sends order confirmation back to customer via WhatsApp
- Works 24/7 — overnight messages are parsed and ready for morning review

#### 2. Proactive Customer Retention & Reorder Nudges

**What it does:**
- Monitors ordering patterns: "The Oak Restaurant orders every Tuesday. It's Wednesday and they haven't ordered."
- Sends personalised nudge via WhatsApp: "Hi Chef, shall we place your usual Tuesday order? 20kg chicken breast, 10kg potatoes, 5L olive oil?"
- Detects churn signals: declining order frequency, shrinking basket size (quantity reductions only — no product switching tracking)
- Alerts field rep via dashboard: "Customer X is at risk. Order frequency down 40% over 4 weeks."

#### 3. Order Confirmation & Modification

**What it does:**
- After wholesaler approves on dashboard, auto-generates line-by-line confirmation → sends to customer via WhatsApp
- Handles substitution communication (wholesaler picks substitute, agent communicates it)
- Customers reply via WhatsApp to modify ("Actually make it 30kg chicken instead of 20kg") → agent re-parses → sends updated order back to dashboard for re-approval

### TIER 2 — Build If Time Allows

#### 4. Simple Invoicing
- On request, send customer an invoice summary via WhatsApp: current balance, items ordered, quantities, prices
- No payment links, no payment prediction, no dunning

#### 5. Demand Prediction Intelligence
- Analyse historical order patterns to predict likely demand in coming weeks
- Factor in seasonal patterns
- Display on wholesaler dashboard as a planning tool — no automated actions

---

## Part 3: Interaction Model

```
    CUSTOMER SIDE                                    WHOLESALER SIDE
    ─────────────                                    ───────────────

    ┌─────────────┐                                  ┌───────────────────────┐
    │  WhatsApp   │─────┐                       ┌───►│  Wholesaler Dashboard │
    │  (text,     │     │                       │    │  (Web App)            │
    │   voice,    │     │   ┌───────────────┐   │    │                       │
    │   images)   │     └──►│               │───┘    │  • Order overview     │
    └─────────────┘         │  AGENT SYSTEM │        │  • Pending orders     │
                            │               │◄───────│  • Approve / Reject   │
                            └───────┬───────┘        │  • Customer health    │
                                    │                │  • Reorder alerts     │
                                    ▼                │  • Agent activity log │
                            ┌───────────────┐        └───────────────────────┘
                            │  Product      │
                            │  Catalogue    │
                            │  + Order      │
                            │  History      │
                            └───────────────┘
```

### Key Principle: No New Tool for the Customer

Customer keeps using WhatsApp. No app, no portal. The agent is invisible to them.

### Human-in-the-Loop: Wholesaler Confirms Everything

The agent **never** sends an order confirmation without the wholesaler's explicit approval:

1. Customer sends WhatsApp message
2. Agent parses and structures the order
3. Order appears on dashboard as **Pending Confirmation**
4. Wholesaler clicks **Yes** (confirm) or **No** (reject/modify)
5. Only after **Yes** → agent sends WhatsApp confirmation to customer

---

## Part 4: Agent Architecture

### Core Concept: One Agent Per Customer

**Containerised customer agents** — one dedicated agent instance per customer. Each holds the full context for that customer (order history, conversation history, preferences, typical basket). Each agent becomes an expert on its specific customer.

A **Wholesaler Orchestrator Agent** sits above all customer agents, coordinating between them and managing the dashboard.

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     1. MESSAGE INGRESS                               │
│                                                                      │
│                  ┌──────────────────────┐                            │
│                  │  WhatsApp Gateway    │                            │
│                  │  (Meta Business API) │                            │
│                  └──────────┬───────────┘                            │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 2. CUSTOMER IDENTIFICATION                            │
│                                                                      │
│                  Phone number → Customer ID lookup                    │
│                  (If unknown number → flag as new customer)          │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 3. CUSTOMER AGENT (one per customer)                  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Context loaded: customer.txt                                │   │
│  │  (order history, conversation history, preferences,          │   │
│  │   typical basket, delivery schedule)                         │   │
│  │                                                              │   │
│  │  Steps:                                                      │   │
│  │  a. Send message + context to LLM                            │   │
│  │  b. LLM classifies intent:                                   │   │
│  │     • place_order → parse items, match SKUs, validate        │   │
│  │     • repeat_order → retrieve last order, propose repeat     │   │
│  │     • modify_order → parse changes to existing pending order │   │
│  │     • remind_last_order → summarise recent orders            │   │
│  │     • general_inquiry → answer from context                  │   │
│  │  c. Return structured output to Orchestrator                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Tools available to Customer Agent:                                  │
│  • search_product_catalogue(query) → fuzzy SKU match                │
│  • get_customer_history(customer_id) → past orders for context      │
│  • get_customer_context(customer_id) → load customer.txt            │
│  • flag_anomaly(order_id, reason) → quantity/pattern anomalies      │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│           4. WHOLESALER ORCHESTRATOR AGENT                           │
│                                                                      │
│  Receives structured output from Customer Agents and:                │
│                                                                      │
│  For ORDERS (place_order, repeat_order):                             │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ a. Create pending order event                          │         │
│  │    (customer_id, products, quantities, LLM reasoning)  │         │
│  │ b. Push to Dashboard → status: Pending Confirmation    │         │
│  │ c. Wait for wholesaler human decision (Yes / No)       │         │
│  │ d. If Yes → trigger outbound WhatsApp confirmation     │         │
│  │ e. If No → call placeholder / flag for manual handling │         │
│  └────────────────────────────────────────────────────────┘         │
│                                                                      │
│  For DIRECT RESPONSES (remind_last_order, general_inquiry):          │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ a. Generate response from Customer Agent output        │         │
│  │ b. Send immediately via WhatsApp (no approval needed)  │         │
│  └────────────────────────────────────────────────────────┘         │
│                                                                      │
│  Tools available to Orchestrator:                                    │
│  • create_pending_order(customer_id, items[]) → dashboard           │
│  • send_whatsapp_message(customer_id, message) → outbound           │
│  • update_order_status(order_id, status) → confirmed/rejected       │
│  • create_alert(type, customer_id, details) → dashboard alert       │
│  • log_agent_action(action, details) → audit trail                  │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              5. NUDGE SCHEDULER (background process)                 │
│                                                                      │
│  Runs on a schedule (e.g., daily at 08:00):                          │
│  a. Scan all customer order patterns for overdue reorders            │
│  b. For each overdue customer, invoke that Customer Agent to         │
│     generate a personalised reorder suggestion                       │
│  c. Route suggestion through Orchestrator:                           │
│     • Low risk (1-2 days late) → send nudge via WhatsApp directly   │
│     • High risk (7+ days late) → create churn alert on dashboard    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              6. AUDIT & TRACE STORE                                   │
│                                                                      │
│  Every interaction is persisted:                                     │
│  • Incoming message (raw)                                            │
│  • Customer context snapshot used                                    │
│  • LLM input/output                                                  │
│  • Intent classification                                             │
│  • Human confirmation decision (if applicable)                       │
│  • Final order state                                                 │
│  • Timestamps throughout                                             │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Summary

| Agent | Scope | Lifecycle | Key Responsibility |
|-------|-------|-----------|-------------------|
| **Customer Agent** (N instances) | One per customer | Spawned on first message, persists context | Parse messages, classify intent, match products, build structured orders |
| **Wholesaler Orchestrator** (1 instance) | Global | Always running | Route orders to dashboard, handle approvals, send confirmations, manage alerts |
| **Nudge Scheduler** (1 instance) | Global | Runs on cron schedule | Detect overdue reorders, generate nudges, flag churn risk |

---

## Part 5: Tech Stack

### Tech Choices for Hackathon (30h)

| Layer | Technology | Why this choice |
|-------|-----------|----------------|
| **LLM** | Claude API (claude-sonnet-4-6) | Best tool-use / agentic capabilities; fast; cost-effective |
| **Agent Framework** | Python + Claude tool-use (native) | Simpler than LangGraph for hackathon; native tool use suffices for multi-step workflows |
| **Backend** | FastAPI (Python) | Lightweight, async-native, fast to prototype |
| **Database** | SQLite (→ PostgreSQL in prod) | Zero setup; sufficient for demo; easy to seed with mock data |
| **Frontend** | Next.js + Tailwind CSS | Fast to build a polished dashboard; SSR for real-time updates |
| **WhatsApp** | Meta WhatsApp Business Cloud API | Direct Meta integration; production-grade; supports text, voice, and image messages |
| **Image parsing** | Claude Vision (multimodal) | Reads handwritten order lists and photo order sheets directly |
| **Voice transcription** | Whisper API | Transcribe WhatsApp voice notes before passing to Customer Agent |
| **Deployment** | Vercel (frontend) + Railway/Fly.io (backend) | See deployment note below |
| **Scheduling** | APScheduler or Celery Beat | For periodic tasks: reorder nudges, churn scanning |
| **Webhook** | FastAPI endpoint | Receives WhatsApp webhook callbacks from Meta API |

### Deployment Note: Vercel vs OpenShift

We evaluated **OpenShift** (Red Hat's Developer Sandbox) vs **Vercel**:

| | Vercel (free tier) | OpenShift Developer Sandbox |
|---|---|---|
| **Cost** | Free | Free (30-day trial, then expires) |
| **Next.js support** | Native (Vercel built Next.js) | Requires manual container setup |
| **Setup time** | Minutes (git push to deploy) | Hours (container config, routes, builds) |
| **SSL/Domain** | Automatic | Manual configuration |
| **Persistence** | Needs external DB anyway | Same |
| **Hackathon fit** | Excellent | Overkill for 30h build |

**Decision: Stick with Vercel.** It's free, zero-config for Next.js, and lets us focus on the product rather than infrastructure. OpenShift makes sense for production (Kubernetes, scaling, enterprise compliance) but not for a hackathon demo. Railway/Fly.io for the FastAPI backend are also free-tier and simple to deploy.

### Frontend Design Direction

Built following `SKILL.md` principles — distinctive, production-grade, visually memorable.

- **Purpose**: Operational command centre for a wholesaler managing incoming orders and customer relationships
- **Tone**: Industrial-utilitarian meets modern data dashboard — clean, functional, high-information-density, with refined typography and purposeful colour to signal order status
- **Core views**:
  - **Order Overview**: Total order value across all customers (aggregated), number of pending/confirmed/rejected orders today, revenue trend. In the demo with a single modelled customer, this shows that customer's total order value.
  - **Order Queue**: List of pending orders with customer name, parsed items, confidence score, anomaly flags, and Approve/Reject buttons
  - **Customer Health**: Grid/list of customers with health scores, last order date, trend indicators
  - **Alerts**: Churn warnings, anomaly flags, nudge results
  - **Activity Log**: Audit trail of all agent actions with timestamps
- **Typography**: Distinctive, highly legible sans-serif for data; characterful display font for headings
- **Colour system**: Status-driven — green (confirmed), amber (pending), red (flagged/churn risk). Neutral background, bold status accents.
- **Motion**: Subtle transitions for new orders appearing in the queue; smooth approve/reject animations

---

## Part 6: Data Model

```sql
-- Core entities
customers (id, name, type, contact_phone, contact_whatsapp,
           delivery_address, health_score, created_at)

products  (id, name, sku, category, unit, price_default,
           created_at)

-- Customer context (the "customer.txt" equivalent)
customer_context (customer_id, context_json, last_updated)
-- context_json holds: typical basket, order patterns, preferences,
-- delivery schedule, conversation notes

-- Customer-specific pricing (optional — skip if complex)
customer_prices (customer_id, product_id, price, valid_from, valid_to)

-- Orders (from customers)
orders    (id, customer_id, channel, raw_message, status,
           total_value, created_at, confirmed_at, confirmed_by)
           -- channel: whatsapp (only channel for MVP)
           -- status: received | parsed | pending_confirmation |
           --         confirmed | rejected | fulfilled

order_items (id, order_id, product_id, quantity, unit_price,
             matched_confidence, original_text, substitution_for)

-- Agent activity log
agent_actions (id, agent_type, action, entity_type, entity_id,
               details_json, confidence, human_reviewed, created_at)
               -- agent_type: customer_agent | orchestrator | nudge_scheduler

-- Conversation memory (per customer)
conversations (id, customer_id, channel, direction, message_text,
               parsed_intent, created_at)
               -- direction: inbound | outbound

-- Order patterns (precomputed for reorder nudges)
order_patterns (customer_id, product_id, avg_interval_days,
                avg_quantity, last_order_date, next_expected_date,
                confidence)
```

---

## Part 7: Demo Scenario

**Scenario: Monday morning at Rheinfood, Cologne**

1. **[22:30 Sunday]** Chef Meyer sends a WhatsApp message: "Hi, I need for tomorrow 20kg chicken breast, 10kg potatoes, and the usual olive oil. Oh, do you still have the Italian tomatoes?"

2. **[22:30 Sunday]** The Customer Agent (Meyer's dedicated agent) activates:
   - Identifies Chef Meyer from phone number
   - Loads Meyer's context: regular customer, orders every Monday, typical basket includes chicken, potatoes, olive oil (5L extra virgin)
   - Parses the message → matches to SKUs → builds structured order
   - Flags: "Italian tomatoes" — not in usual basket, notes it as a question (not a firm order line)
   - Sends structured order to the Orchestrator → creates a **Pending** order on the dashboard

3. **[06:00 Monday]** Inside sales team arrives. Dashboard shows:
   - **Order Overview**: Total pending order value: €1,247.80 across 12 orders parsed overnight
   - 1 flagged: quantity anomaly (a customer ordered 500 units instead of their usual 50)
   - 1 flagged: unknown phone number (potential new customer)
   - Chef Meyer's order ready to approve with a note: "Customer asked about Italian tomatoes — not added as order line, may need follow-up"

4. **[06:05 Monday]** Sales rep clicks **Yes** on Meyer's order → WhatsApp confirmation sent:
   > "Order confirmed, Chef Meyer:
   > - 20kg chicken breast (€4.20/kg) — €84.00
   > - 10kg potatoes (€1.10/kg) — €11.00
   > - 5L olive oil extra virgin (€8.90/L) — €44.50
   > Total: €139.50 — Delivery: Monday before 10:00
   >
   > Re: Italian tomatoes — checking availability, we'll let you know!"

5. **[10:00 Tuesday]** The Oak Restaurant hasn't placed their usual Tuesday order. Nudge Scheduler detects this, invokes The Oak's Customer Agent, generates a personalised suggestion:
   > "Hi Chef Davis, your usual Tuesday order is still open. Shall we place it? 15kg pork tenderloin, 8kg onions, 20L cooking oil. Just reply 'Yes' to confirm or send any changes."

6. **[10:05 Tuesday]** Chef Davis replies "Yes". Customer Agent parses the confirmation, Orchestrator creates a pending order on the dashboard. Sales rep approves. Confirmation sent.

---

## Part 8: Hackathon vs. Production Scope

| Capability | Hackathon (30h) | Production |
|------------|-----------------|------------|
| **Order channels** | WhatsApp only (Meta Business API) | + Email, Voice, Web portal |
| **Product catalogue** | ~200 mock SKUs (beverages, dairy, meat, produce, dry goods) | Full ERP integration, 5,000–25,000 SKUs |
| **Customer data** | 10–20 mock customers with order histories | Full ERP customer master |
| **Agent confidence** | Fixed threshold (e.g., 0.85) | Adaptive per customer; learning from corrections |
| **Stock management** | Infinite stock (no tracking) | Real inventory with supplier procurement |
| **Dashboard** | Order overview + queue + approval buttons + customer health + alerts | Full analytics, reporting, team management |
| **Authentication** | None (demo mode) | SSO, role-based access |
| **Deployment** | Vercel (frontend) + Railway/Fly.io (backend) | Multi-tenant SaaS |
| **Language** | English | English (expand later based on market needs) |

---

## Part 9: Implementation Todo List (TIER 1 Only)

This is the task-level breakdown for building all three TIER 1 features. Phases are roughly sequential — later phases depend on earlier ones — but tasks within a phase can often be parallelised across team members.

---

### Phase 0: Project Scaffolding & Setup
> Goal: Everyone can run the project locally and push to a shared repo.

- [ ] **0.1** Initialise monorepo structure: `/backend` (FastAPI/Python), `/frontend` (Next.js), `/data` (seed files)
- [ ] **0.2** Set up Python backend: FastAPI project with `pyproject.toml` or `requirements.txt`, virtualenv, basic health endpoint (`GET /health`)
- [ ] **0.3** Set up Next.js frontend: `create-next-app` with Tailwind CSS, basic page rendering
- [ ] **0.4** Set up SQLite database file and connection utility in backend (`database.py`)
- [ ] **0.5** Configure environment variables: `ANTHROPIC_API_KEY`, `META_WHATSAPP_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`
- [ ] **0.6** Set up Vercel project for frontend, Railway/Fly.io project for backend (deploy empty shells to confirm pipeline works)
- [ ] **0.7** Register Meta WhatsApp Business Cloud API app: create Meta Developer account, set up test business number, configure webhook URL pointing to backend

---

### Phase 1: Data Layer — Schema, Seed Data, & Context Files
> Goal: Database is populated with realistic mock data that all agents can query.

- [ ] **1.1** Create SQLite schema migration script implementing the data model from Part 6 (customers, products, customer_context, orders, order_items, agent_actions, conversations, order_patterns)
- [ ] **1.2** Write seed script: **products** — ~200 mock SKUs across categories (beverages, dairy, meat, produce, dry goods) with realistic English names, units, and prices
- [ ] **1.3** Write seed script: **customers** — 10–20 mock customers (restaurant names, phone numbers, WhatsApp IDs, delivery addresses, health scores)
- [ ] **1.4** Write seed script: **customer_context** — for each customer, create a `context_json` blob containing: typical basket (product IDs + usual quantities), order frequency (e.g., "every Tuesday"), delivery preferences, any notes
- [ ] **1.5** Write seed script: **order history** — generate 8–12 weeks of historical orders per customer, consistent with their typical basket and frequency. Populate `orders`, `order_items`, and `order_patterns` tables.
- [ ] **1.6** Write seed script: **conversations** — a handful of past WhatsApp messages per customer (inbound orders + outbound confirmations) to populate conversation memory
- [ ] **1.7** Create a single `seed_all.py` script that runs all seed scripts in order and produces a ready-to-use `demo.db`
- [ ] **1.8** Write basic CRUD utility functions: `get_customer_by_phone()`, `get_customer_context()`, `get_products_by_query()`, `get_customer_order_history()`, `create_order()`, `update_order_status()`, `log_agent_action()`, `save_conversation()`

---

### Phase 2: WhatsApp Integration (Meta Business API)
> Goal: Incoming WhatsApp messages arrive at our backend; outbound messages reach the customer's phone.

- [ ] **2.1** Implement webhook verification endpoint: `GET /webhook` — responds to Meta's hub.challenge for webhook registration
- [ ] **2.2** Implement webhook receiver endpoint: `POST /webhook` — receives incoming WhatsApp messages (text, voice, image), extracts sender phone number, message type, and content
- [ ] **2.3** Implement message type handlers:
  - **Text**: extract message body directly
  - **Voice**: download audio file from Meta API → send to Whisper API for transcription → return transcript text
  - **Image**: download image from Meta API → hold as base64 for Claude Vision processing
- [ ] **2.4** Implement outbound message function: `send_whatsapp_message(phone_number, message_text)` — calls Meta Cloud API `POST /{phone_number_id}/messages` to send text replies
- [ ] **2.5** Test end-to-end: send a WhatsApp message to the test number → confirm it arrives at the webhook → confirm a reply is sent back (echo test)
- [ ] **2.6** Add error handling: retry logic for Meta API failures, logging for malformed payloads, graceful handling of unsupported message types

---

### Phase 3: Customer Agent — Intent Classification & Order Parsing
> Goal: Given a raw message + customer context, the agent returns a structured intent + parsed order.

- [ ] **3.1** Define the Customer Agent's system prompt: include role description, available intents (`place_order`, `repeat_order`, `modify_order`, `remind_last_order`, `general_inquiry`), output schema (JSON), instructions to use customer context for fuzzy matching and validation
- [ ] **3.2** Define the Customer Agent's tool schemas for Claude tool-use:
  - `search_product_catalogue(query: str)` → returns top-N matching products with SKU, name, unit, price
  - `get_customer_history(customer_id: str)` → returns recent orders with items
  - `get_customer_context(customer_id: str)` → returns customer.txt context_json
  - `flag_anomaly(details: str)` → records anomaly for orchestrator
- [ ] **3.3** Implement tool handler functions that execute the actual DB queries when Claude calls them
- [ ] **3.4** Implement the Customer Agent orchestration loop: receive message → load customer context → call Claude API with system prompt + tools + message → handle tool calls → return final structured output (intent, parsed items with product IDs/quantities/prices/confidence scores, any flags/anomalies, suggested response text)
- [ ] **3.5** Implement fuzzy product matching logic inside `search_product_catalogue`: string similarity against product names (use `fuzzywuzzy` or similar), return matches above a threshold with confidence scores
- [ ] **3.6** Implement anomaly detection: compare parsed quantities against `order_patterns` table — flag if quantity deviates >3x from historical average
- [ ] **3.7** Handle the `repeat_order` intent: retrieve last order from history, propose it as a new order with same items/quantities
- [ ] **3.8** Handle the `remind_last_order` intent: retrieve recent orders, generate a natural-language summary
- [ ] **3.9** Write unit tests: test with 5–10 sample messages covering each intent type, verify correct parsing, product matching, and anomaly flagging

---

### Phase 4: Wholesaler Orchestrator — Order Routing & Approval Flow
> Goal: Customer Agent output flows into the Orchestrator, which creates pending orders and handles the approval lifecycle.

- [ ] **4.1** Implement the main message processing pipeline: webhook receives message → identify customer by phone → invoke Customer Agent → receive structured output → route to Orchestrator
- [ ] **4.2** Implement Orchestrator logic for **order intents** (`place_order`, `repeat_order`):
  - Create a new `orders` row with status `pending_confirmation`, store `raw_message`, compute `total_value` from parsed items
  - Create `order_items` rows for each parsed product (product_id, quantity, unit_price, matched_confidence, original_text)
  - Log to `agent_actions` table (agent_type: customer_agent, action: parsed_order, details_json with full LLM output)
  - Log to `conversations` table (inbound message)
- [ ] **4.3** Implement Orchestrator logic for **direct response intents** (`remind_last_order`, `general_inquiry`):
  - Take the response text from Customer Agent output
  - Call `send_whatsapp_message()` to reply immediately
  - Log to `agent_actions` and `conversations`
  - No dashboard involvement
- [ ] **4.4** Implement API endpoints for the dashboard to consume:
  - `GET /api/orders?status=pending_confirmation` — list pending orders with items, customer info, flags
  - `GET /api/orders?status=confirmed` — list confirmed orders
  - `GET /api/orders/{id}` — single order detail with items, anomaly flags, LLM reasoning
  - `GET /api/orders/overview` — aggregated stats: total pending value, total confirmed value, count by status
  - `POST /api/orders/{id}/approve` — set status to `confirmed`, trigger outbound WhatsApp confirmation
  - `POST /api/orders/{id}/reject` — set status to `rejected`, call placeholder (no WhatsApp message for now)
- [ ] **4.5** Implement the approval → outbound message flow: when `POST /api/orders/{id}/approve` is called:
  - Update order status to `confirmed`, set `confirmed_at` and `confirmed_by`
  - Generate a line-by-line WhatsApp confirmation message from order_items (product name, quantity, unit price, line total, order total, delivery info)
  - Call `send_whatsapp_message()` to send confirmation to customer
  - Log to `agent_actions` (agent_type: orchestrator, action: order_confirmed)
  - Log to `conversations` (outbound confirmation)
- [ ] **4.6** Implement unknown customer handling: if phone number not found in `customers` table, create a placeholder alert on the dashboard ("New customer — unknown phone number"), store the raw message, skip agent processing
- [ ] **4.7** Write integration tests: simulate a full flow from webhook payload → Customer Agent → Orchestrator → pending order in DB → approval → outbound message mock

---

### Phase 5: Frontend Dashboard (Next.js + Tailwind)
> Goal: Wholesaler can view, approve/reject orders, and see customer health — all from a web dashboard.

- [ ] **5.1** Set up API client in Next.js: configure `fetch` or `axios` calls to the FastAPI backend endpoints from Phase 4.4
- [ ] **5.2** Build **layout shell**: sidebar navigation (Order Overview, Order Queue, Customer Health, Alerts, Activity Log), header with branding, responsive structure
- [ ] **5.3** Build **Order Overview** page:
  - Top-level KPI cards: total pending order value, total confirmed order value today, number of orders by status (pending / confirmed / rejected / flagged)
  - Simple revenue trend (bar or line chart) from historical confirmed orders
- [ ] **5.4** Build **Order Queue** page:
  - Table/card list of pending orders: customer name, order timestamp, parsed items summary, total value, confidence score, anomaly flags
  - Each order has **Approve** (green) and **Reject** (red) buttons
  - Clicking Approve calls `POST /api/orders/{id}/approve` → optimistic UI update → order moves to confirmed
  - Clicking Reject calls `POST /api/orders/{id}/reject` → order moves to rejected
  - Expandable row/modal showing full order detail: each line item (product, quantity, unit price, line total, original text, confidence), LLM reasoning, raw customer message
- [ ] **5.5** Build **Customer Health** page:
  - Grid/list of all customers: name, last order date, order frequency, health score, trend indicator (arrow up/down/flat)
  - Colour-coded health: green (healthy), amber (declining), red (churn risk)
  - Click into a customer → detail view with their recent orders and conversation history
- [ ] **5.6** Build **Alerts** panel:
  - List of alerts: churn warnings, anomaly flags, nudge delivery confirmations
  - Each alert shows: type, customer name, detail text, timestamp
  - Dismissible or acknowledgeable
- [ ] **5.7** Build **Activity Log** page:
  - Chronological list of all agent_actions: timestamp, agent type, action, entity, details
  - Filterable by agent type and date range
- [ ] **5.8** Apply SKILL.md design principles: distinctive typography (not Inter/Roboto), status-driven colour system (green/amber/red), industrial-utilitarian tone, subtle motion for order queue updates (new orders slide in, approve/reject animations)
- [ ] **5.9** Implement polling or WebSocket for real-time updates: dashboard auto-refreshes when new orders arrive or statuses change (simplest: poll `/api/orders` every 5 seconds; stretch: WebSocket via FastAPI)
- [ ] **5.10** Test full UI flow: load dashboard → see pending orders → approve one → confirm it disappears from queue and appears in confirmed → check that WhatsApp confirmation was sent (via backend logs)

---

### Phase 6: Nudge Scheduler — Reorder Detection & Proactive Nudges
> Goal: A background process detects overdue customers and sends WhatsApp nudges.

- [ ] **6.1** Implement `get_overdue_customers(current_date)` query: scan `order_patterns` table for customers whose `next_expected_date` is before today and who have no order with status `received`/`parsed`/`pending_confirmation`/`confirmed` created after `next_expected_date`
- [ ] **6.2** Implement reorder suggestion builder: for an overdue customer, load their `customer_context` (typical basket) → build a proposed reorder with their usual items and quantities
- [ ] **6.3** Implement nudge message generator: use Claude API (lightweight call) to produce a natural, personalised WhatsApp nudge message from the reorder suggestion (e.g., "Hi Chef Davis, your usual Tuesday order is still open. Shall we place it? 15kg pork tenderloin, 8kg onions, 20L cooking oil. Reply 'Yes' to confirm or send changes.")
- [ ] **6.4** Implement risk-level routing:
  - **Low risk** (1–2 days overdue): send nudge via WhatsApp directly
  - **High risk** (7+ days overdue, or declining order frequency over 4+ weeks): create a churn alert on the dashboard instead of (or in addition to) sending a nudge
- [ ] **6.5** Implement the scheduler: use APScheduler to run the nudge scan at a configurable interval (default: daily at 08:00). For the demo, also expose a manual trigger endpoint `POST /api/nudge/run` so we can fire it on demand.
- [ ] **6.6** Handle nudge responses: when a customer replies "Yes" to a nudge, the webhook receives it → Customer Agent classifies as `repeat_order` (the nudge's proposed basket) → flows through the normal Orchestrator → pending order on dashboard → wholesaler approves
- [ ] **6.7** Update `order_patterns` after each confirmed order: recalculate `avg_interval_days`, `avg_quantity`, `last_order_date`, `next_expected_date` for the products in that order
- [ ] **6.8** Log all nudge activity to `agent_actions` (agent_type: nudge_scheduler) and `conversations` (outbound nudge message)
- [ ] **6.9** Write tests: create a customer with an overdue pattern, run nudge scan, verify nudge message is generated and sent (or alert created for high-risk)

---

### Phase 7: Order Confirmation & Modification (TIER 1 Feature #3)
> Goal: Customers can modify orders via WhatsApp; modifications flow back through the approval loop.

- [ ] **7.1** Implement `modify_order` intent handling in Customer Agent: when a customer sends a follow-up message that references an existing pending order (e.g., "Actually make it 30kg chicken instead of 20kg"), the agent:
  - Identifies the pending order (most recent pending order for this customer)
  - Parses the modification (which item, new quantity)
  - Returns structured output with intent `modify_order`, original order ID, and updated items
- [ ] **7.2** Implement Orchestrator handling for `modify_order`:
  - Update the existing order's `order_items` (change quantity, recalculate line price and total)
  - Reset order status to `pending_confirmation` (if it was already pending, it stays; this handles edge cases)
  - Log the modification in `agent_actions`
  - Dashboard shows the updated order with a "Modified" badge and a diff (what changed)
- [ ] **7.3** Implement substitution communication flow: when the wholesaler rejects an order or flags a specific item for substitution:
  - `POST /api/orders/{id}/substitute` with `{ item_id, substitute_product_id }`
  - Orchestrator generates a WhatsApp message: "Item X is currently unavailable. We suggest Y instead at €Z/kg. Reply 'OK' to confirm or let us know your preference."
  - Customer's reply flows back through the normal agent pipeline
- [ ] **7.4** Implement confirmation message formatting: after approval, generate a detailed WhatsApp message with line items, quantities, unit prices, line totals, order total, and expected delivery window
- [ ] **7.5** Write tests: send an order → modify it via follow-up message → verify order_items updated → approve → verify confirmation message includes the modified quantities

---

### Phase 8: Integration Testing & Demo Polish
> Goal: The full end-to-end flow works reliably for the demo scenario described in Part 7.

- [ ] **8.1** Run the full demo scenario end-to-end:
  1. Send WhatsApp message as Chef Meyer → verify it arrives at webhook → Customer Agent parses → pending order on dashboard
  2. Approve on dashboard → WhatsApp confirmation sent to Chef Meyer
  3. Trigger nudge scan → verify The Oak Restaurant gets a nudge
  4. Reply "Yes" as Chef Davis → pending order created → approve → confirmation sent
- [ ] **8.2** Seed the demo database with the specific scenario data: Chef Meyer's context, The Oak Restaurant's context, their order patterns, product catalogue entries for the items mentioned in the demo
- [ ] **8.3** Polish error states: what happens if the LLM fails to parse? (Show "Unable to parse — manual review required" on dashboard with raw message). What if WhatsApp API is down? (Queue the outbound message for retry.)
- [ ] **8.4** Polish dashboard UI: ensure loading states, empty states, and transitions are smooth. Verify the Order Overview numbers update correctly after approvals.
- [ ] **8.5** Deploy to Vercel (frontend) + Railway/Fly.io (backend). Update Meta webhook URL to point to deployed backend. Verify the full flow works over the internet (not just localhost).
- [ ] **8.6** Prepare demo script: step-by-step walkthrough matching the Part 7 scenario, with pre-prepared WhatsApp messages to send, and talking points for each dashboard screen.

---

### Phase Summary & Dependencies

```
Phase 0: Project Scaffolding ──────────────────────────┐
                                                        │
Phase 1: Data Layer ───────────────────────────────────┤
                                                        │
Phase 2: WhatsApp Integration ─────────────────────────┤
                                                        │
           ┌────────────────────────────────────────────┘
           │ (Phases 1 + 2 must complete before Phase 3)
           ▼
Phase 3: Customer Agent ───────────────────────────────┐
                                                        │
           ┌────────────────────────────────────────────┘
           │ (Phase 3 must complete before Phase 4)
           ▼
Phase 4: Orchestrator + API ───────────────────────────┐
                                                        │
           ┌────────────────────────────────────────────┤
           │ (Phase 4 must complete before Phases 5-7)  │
           ▼                                            ▼
Phase 5: Frontend Dashboard          Phase 6: Nudge Scheduler
           │                                   │
           │         Phase 7: Order Modification
           │              (needs Phases 4 + 5)
           │                    │
           └────────┬───────────┘
                    ▼
          Phase 8: Integration & Demo Polish
```

**Parallelisation opportunities:**
- Phase 1 (data) and Phase 2 (WhatsApp) can be done in parallel by different team members
- Phase 5 (frontend) and Phase 6 (nudge scheduler) can be done in parallel once Phase 4 is complete
- Phase 0 should be done first by one person, then everyone branches out

---

## Sources

- [Choco OrderAgent](https://choco.com/us/orderagent) — AI order processing for food distributors
- [Orderlion AI Inbox](https://www.orderlion.com/en) — Multi-channel order conversion
- [kollex](https://www.kollex.de/) — Digital ordering for beverage wholesale
- [metasfresh ERP](https://metasfresh.com/) — Open-source ERP for food & wholesale
- [Meta WhatsApp Business Platform](https://developers.facebook.com/docs/whatsapp/cloud-api) — WhatsApp Cloud API documentation
- [SKILL.md](./SKILL.md) — Frontend design skill reference
- [demo_logic.md](./demo_logic.md) — Architecture flow reference
