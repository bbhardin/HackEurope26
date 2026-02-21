# User Touchpoints & Tech Stack Design — V2 (Implementation Guide)

## Part 1: Scope & Actors

### Who are the actors?

For the hackathon MVP, we focus on **two actors only**. Suppliers are out of scope — we assume the wholesaler has infinite stock.

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
- **Up to 50 employees**
- Mid-size regional wholesalers (revenue €20M–200M)
- Currently relying on phone, WhatsApp, email, fax for order intake
- No dedicated IT teams

### MVP Assumptions
- **Infinite stock** — no supplier or procurement logic
- **WhatsApp only** — single communication channel for customer interactions
- **Customers order the same items** — only quantity varies, not product type
- **English language** for all interfaces and messages

---

## Part 2: Prioritised Touchpoints

### TIER 1 — "Build This at the Hackathon"

#### 1. Order Placement (WhatsApp Inbox)
**Current state:** Orders arrive via WhatsApp at all hours. Inside sales staff manually transcribe them into the ERP during business hours. After-hours orders (chefs ordering at 22:00–midnight) pile up as unread messages.

**What our agent does:**
- Ingests orders from **WhatsApp** (text messages, voice notes via transcription, photos of handwritten lists)
- Parses unstructured natural language into a structured order (product, quantity, unit, delivery date)
- Maps to product catalogue using fuzzy matching ("the usual cheese, but the big one" → Emmentaler 500g)
- Flags anomalies: "This customer usually orders 50 cases. They ordered 500. Confirm?"
- **Does NOT auto-confirm** — sends the parsed order to the wholesaler dashboard for approval
- After wholesaler confirms, sends order confirmation back to customer via WhatsApp
- Works 24/7 — processes overnight messages so they're ready for review when the morning shift starts

**Why this is our #1 wedge:**
- Eliminates the largest labour cost centre (inside sales doing data entry)
- Choco's OrderAgent proves the concept (50% of orders need no manual review), but Choco is a platform — customers must move onto Choco. Our agent **meets customers where they already are** (WhatsApp) with zero behaviour change required.

#### 2. Proactive Customer Retention & Reorder Nudges
**Current state:** Churn detection is informal (a rep notices someone stopped ordering). No automated reorder suggestions. When a rep leaves, customer relationships go with them.

**What our agent does:**
- Monitors ordering patterns: "The Oak Restaurant orders every Tuesday. It's Wednesday and they haven't ordered."
- Sends personalised nudge via WhatsApp: "Hi Chef, shall we place your usual Tuesday order? 20kg chicken breast, 10kg potatoes, 5L olive oil?"
- Detects churn signals: declining order frequency, shrinking basket size (quantity reductions only — we don't track product switching)
- Alerts the field rep via the dashboard with context: "Customer X is at risk. Order frequency down 40% over 4 weeks. Last complaint: late delivery on 12 Feb."

**Why this is our #2 wedge:**
- Greenfield opportunity — nobody does proactive retention well for mid-market wholesalers
- Directly protects revenue, not just saves cost. Easy to demonstrate ROI.
- Minimal integration — just needs historical order data

#### 3. Order Confirmation & Modification
**What our agent does:**
- After the wholesaler approves an order on the dashboard, auto-generates a line-by-line confirmation and sends it to the customer via WhatsApp
- Handles substitution suggestions when the wholesaler flags an out-of-stock item (wholesaler picks the substitute, agent communicates it)
- Customers can reply via WhatsApp to modify orders (e.g., "Actually make it 30kg chicken instead of 20kg") — the agent re-parses and sends updated order back to the dashboard for re-approval

**Why this is our #3 wedge:**
- Closes the loop on the order flow — without this, the system only does intake, not fulfilment communication
- Keeps the wholesaler in control (all confirmations require human approval)
- Customers interact naturally via WhatsApp — no portals or apps needed

---

### TIER 2 — "Build If Time Allows" (Nice-to-have)

#### 4. Simple Invoicing
- On request, send the customer an invoice summary via WhatsApp: current balance, items ordered, quantities, and prices
- No payment links, no payment prediction, no dunning logic
- Just an overview for the customer's records

#### 5. Demand Prediction Intelligence
- Analyse historical order patterns across all customers to predict likely demand in the coming weeks
- Factor in seasonal patterns (e.g., higher meat orders before holidays, beverage spikes in summer)
- Present predictions on the wholesaler dashboard as a planning tool
- The wholesaler uses this to plan ahead — no automated actions taken

---

## Part 3: The Interaction Model

### How does the agent actually interact with users?

```
    CUSTOMER SIDE                                    WHOLESALER SIDE
    ─────────────                                    ───────────────

    ┌─────────────┐                                  ┌───────────────────────┐
    │  WhatsApp   │─────┐                       ┌───►│  Wholesaler Dashboard │
    │  (text,     │     │                       │    │  (Web App)            │
    │   voice,    │     │   ┌───────────────┐   │    │                       │
    │   images)   │     └──►│               │───┘    │  • Pending orders     │
    └─────────────┘         │  AGENT SYSTEM │        │  • Approve / Reject   │
                            │               │◄───────│  • Customer health    │
                            └───────┬───────┘        │  • Reorder alerts     │
                                    │                │  • Demand predictions  │
                                    ▼                │  • Agent activity log  │
                            ┌───────────────┐        └───────────────────────┘
                            │  Product      │
                            │  Catalogue    │
                            │  + Order      │
                            │  History      │
                            └───────────────┘
```

### Key design principle: NO NEW TOOL FOR THE CUSTOMER

The customer (restaurant chef) keeps using WhatsApp. They never download an app or log into a portal. The agent is invisible to them — they just notice that orders get confirmed faster, mistakes go down, and someone proactively reminds them to reorder.

The **wholesaler** gets a dashboard to:
- See all pending orders (parsed by the agent, awaiting approval)
- Approve or reject orders with one click
- Monitor customer health scores and churn risk
- View demand predictions
- Review agent activity log and override decisions

### Human-in-the-Loop: The Wholesaler Confirms Everything

This is a critical design principle. The agent **never** sends an order confirmation to the customer without the wholesaler's explicit approval. The flow is:

1. Customer sends WhatsApp message
2. Agent parses and structures the order
3. Order appears on dashboard as **Pending Confirmation**
4. Wholesaler clicks **Yes** (confirm) or **No** (reject/modify)
5. Only after **Yes** → agent sends WhatsApp confirmation to customer

---

## Part 4: Agent Architecture

### Core Concept: One Agent Per Customer

Rather than a single monolithic agent, we use **containerised customer agents** — one dedicated agent instance per customer. Each customer agent holds the full context for that customer (order history, conversation history, preferences, typical basket). This means each agent becomes an expert on its specific customer.

A **Wholesaler Orchestrator Agent** sits above all customer agents, coordinating between them and managing the wholesaler-facing dashboard.

### Architecture Flow (based on demo_logic.md)

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
│                                                                      │
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

### Concrete Tech Choices for Hackathon (30h)

| Layer | Technology | Why this choice |
|-------|-----------|----------------|
| **LLM** | Claude API (claude-sonnet-4-6) | Best tool-use / agentic capabilities; fast; cost-effective for high volume |
| **Agent Framework** | Python + Claude tool-use (native) | Simpler than LangGraph for hackathon; Claude's native tool use is sufficient for multi-step workflows |
| **Backend** | FastAPI (Python) | Lightweight, async-native, fast to prototype |
| **Database** | SQLite (→ PostgreSQL in prod) | Zero setup; sufficient for demo; easy to seed with mock data |
| **Frontend** | Next.js + Tailwind CSS | Fast to build a polished dashboard; SSR for real-time updates |
| **WhatsApp** | Meta WhatsApp Business Cloud API | Direct integration with Meta's platform; production-grade; supports text, voice, and image messages |
| **Image parsing** | Claude Vision (multimodal) | Can read handwritten order lists and photos of order sheets directly |
| **Voice transcription** | Whisper API | Transcribe WhatsApp voice notes before passing to Customer Agent |
| **Deployment** | Vercel (frontend) + Railway/Fly.io (backend) | Fast deployment, free tiers available |
| **Scheduling** | APScheduler or Celery Beat | For periodic tasks: reorder nudges, churn scanning |
| **Webhook** | FastAPI endpoint | Receives WhatsApp webhook callbacks from Meta API |

### Frontend Design Direction

The wholesaler dashboard should be built following the principles in `SKILL.md` — distinctive, production-grade, and visually memorable. Key aspects:

- **Purpose**: Operational command centre for a wholesaler managing incoming orders and customer relationships
- **Tone**: Industrial-utilitarian meets modern data dashboard — clean, functional, high-information-density, but with refined typography and purposeful use of colour to signal order status (pending, confirmed, flagged)
- **Core views**:
  - **Order Queue**: List of pending orders with customer name, parsed items, confidence score, anomaly flags, and Approve/Reject buttons
  - **Customer Health**: Grid/list of customers with health scores, last order date, trend indicators
  - **Alerts**: Churn warnings, anomaly flags, nudge results
  - **Activity Log**: Audit trail of all agent actions with timestamps
- **Typography**: Choose a distinctive, highly legible sans-serif for data display; pair with a characterful display font for headings
- **Colour system**: Status-driven — green (confirmed), amber (pending), red (flagged/churn risk). Neutral background, bold status accents.
- **Motion**: Subtle transitions for new orders appearing in the queue; smooth approve/reject animations

---

## Part 6: Data Model (Simplified for MVP)

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
           created_at, confirmed_at, confirmed_by)
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

## Part 7: Demo Scenario — The "Wow" Moment

**Scenario: Monday morning at Rheinfood, Cologne**

1. **[22:30 Sunday]** Chef Meyer sends a WhatsApp message: "Hi, I need for tomorrow 20kg chicken breast, 10kg potatoes, and the usual olive oil. Oh, do you still have the Italian tomatoes?"

2. **[22:30 Sunday]** The Customer Agent (Meyer's dedicated agent) activates:
   - Identifies Chef Meyer from phone number
   - Loads Meyer's context: regular customer, orders every Monday, typical basket includes chicken, potatoes, olive oil (5L extra virgin)
   - Parses the message → matches to SKUs → builds structured order
   - Flags: "Italian tomatoes" — not in usual basket, notes it as a question (not a firm order line)
   - Sends structured order to the Orchestrator → creates a **Pending** order on the dashboard

3. **[06:00 Monday]** Inside sales team arrives. Dashboard shows:
   - **12 orders auto-parsed overnight** — all awaiting confirmation
   - 1 flagged: quantity anomaly (a customer ordered 500 units instead of their usual 50)
   - 1 flagged: unknown phone number (potential new customer)
   - Chef Meyer's order ready to approve with a note: "Customer asked about Italian tomatoes — not added as order line, may need follow-up"

4. **[06:05 Monday]** Sales rep clicks **Yes** on Meyer's order → WhatsApp confirmation is sent automatically:
   > "Order confirmed, Chef Meyer:
   > - 20kg chicken breast (€4.20/kg) — €84.00
   > - 10kg potatoes (€1.10/kg) — €11.00
   > - 5L olive oil extra virgin (€8.90/L) — €44.50
   > Total: €139.50 — Delivery: Monday before 10:00
   >
   > Re: Italian tomatoes — checking availability, we'll let you know!"

5. **[10:00 Tuesday]** The Oak Restaurant hasn't placed their usual Tuesday order. Nudge Scheduler detects this, invokes The Oak's Customer Agent, generates a personalised suggestion. WhatsApp nudge sent:
   > "Hi Chef Davis, your usual Tuesday order is still open. Shall we place it? 15kg pork tenderloin, 8kg onions, 20L cooking oil. Just reply 'Yes' to confirm or send any changes."

6. **[10:05 Tuesday]** Chef Davis replies "Yes". Customer Agent parses the confirmation, Orchestrator creates a pending order on the dashboard. Sales rep approves. Confirmation sent.

---

## Part 8: Hackathon Scope vs. Production Scope

| Capability | Hackathon (30h) | Production |
|------------|-----------------|------------|
| **Order channels** | WhatsApp only (Meta Business API) | + Email, Voice (Twilio), Web portal |
| **Product catalogue** | ~200 mock SKUs (beverages, dairy, meat, produce, dry goods) | Full ERP integration, 5,000–25,000 SKUs |
| **Customer data** | 10–20 mock customers with order histories | Full ERP customer master |
| **Agent confidence** | Fixed threshold (e.g., 0.85) | Adaptive per customer; learning from corrections |
| **Stock management** | Infinite stock (no tracking) | Real inventory with supplier procurement |
| **Dashboard** | Order queue + approval buttons + customer health + alerts | Full analytics, reporting, team management |
| **Authentication** | None (demo mode) | SSO, role-based access |
| **Deployment** | Local + demo URL | Multi-tenant SaaS |
| **Language** | English | + German, French, Dutch, Italian, Polish |

---

## Sources

- [Choco OrderAgent](https://choco.com/us/orderagent) — AI order processing for food distributors
- [Orderlion AI Inbox](https://www.orderlion.com/en) — Multi-channel order conversion
- [kollex](https://www.kollex.de/) — Digital ordering for beverage wholesale
- [metasfresh ERP](https://metasfresh.com/) — Open-source ERP for food & wholesale
- [Meta WhatsApp Business Platform](https://developers.facebook.com/docs/whatsapp/cloud-api) — WhatsApp Cloud API documentation
- [SKILL.md](./SKILL.md) — Frontend design skill reference
- [demo_logic.md](./demo_logic.md) — Architecture flow reference
