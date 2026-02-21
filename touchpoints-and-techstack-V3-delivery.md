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

## Sources

- [Choco OrderAgent](https://choco.com/us/orderagent) — AI order processing for food distributors
- [Orderlion AI Inbox](https://www.orderlion.com/en) — Multi-channel order conversion
- [kollex](https://www.kollex.de/) — Digital ordering for beverage wholesale
- [metasfresh ERP](https://metasfresh.com/) — Open-source ERP for food & wholesale
- [Meta WhatsApp Business Platform](https://developers.facebook.com/docs/whatsapp/cloud-api) — WhatsApp Cloud API documentation
- [SKILL.md](./SKILL.md) — Frontend design skill reference
- [demo_logic.md](./demo_logic.md) — Architecture flow reference
