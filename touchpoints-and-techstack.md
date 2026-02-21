# User Touchpoints & Tech Stack Design

## Part 1: The Complete Touchpoint Map

### Who are the actors?

```
┌─────────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│   CUSTOMERS      │         │   WHOLESALER          │         │   SUPPLIERS      │
│                  │         │                       │         │                  │
│ • Restaurants    │◄───────►│ • Inside sales team   │◄───────►│ • Manufacturers  │
│ • Hotels         │         │ • Field reps          │         │ • Farmers/       │
│ • Caterers       │         │ • Warehouse staff     │         │   Producers      │
│ • Small retail   │         │ • Procurement team    │         │ • Importers      │
│ • Canteens       │         │ • Delivery drivers    │         │ • Other          │
│                  │         │ • Finance/credit      │         │   wholesalers    │
└─────────────────┘         └──────────────────────┘         └─────────────────┘
```

### The 12 Touchpoints — Prioritised by Agent Impact

We analysed every touchpoint in the wholesaler ↔ customer relationship. Here's what matters for our hackathon MVP vs. what we defer.

---

#### TIER 1 — "Build This at the Hackathon" (Highest impact, most differentiated)

##### 1. Order Placement (Multi-Channel Inbox)
**Current state:** 70–80% of orders arrive via phone, fax, WhatsApp, email. Inside sales staff (Innendienst) manually transcribe 500–2,000 orders/day into the ERP. Error rates: 1–3%. After-hours orders (chefs order at 22:00–midnight) pile up as voicemails.

**What our agent does:**
- Ingests orders from **email, WhatsApp, voice (transcribed), photo of handwritten list, PDF/fax**
- Parses unstructured natural language → structured order (product, quantity, unit, delivery date)
- Maps to product catalogue using fuzzy matching ("the usual cheese, but the big one" → Emmentaler 500g)
- Flags anomalies: "This customer usually orders 50 cases. They ordered 500. Confirm?"
- Sends instant order confirmation back to customer via same channel
- Works 24/7 — processes the 22:00 voicemails before the 6 AM shift starts

**Why this is our #1 wedge:**
- Eliminates the single largest labour cost centre (inside sales team doing data entry)
- Choco's OrderAgent already proves the concept works (50% of orders need no manual review)
- BUT Choco is a platform — you must move your ordering onto Choco. Our agent **meets the customer where they are** (their existing email/WhatsApp) without requiring behaviour change.

##### 2. Proactive Customer Retention & Reorder Nudges
**Current state:** Churn detection is informal (a rep notices someone stopped ordering). No automated reorder suggestions. Over-reliance on field reps — when a rep leaves, relationships go with them.

**What our agent does:**
- Monitors ordering patterns: "Restaurant Zum Löwen orders every Tuesday. It's Wednesday and they haven't ordered."
- Sends personalised nudge via WhatsApp/email: "Hi Chef, sollen wir Ihre übliche Dienstagbestellung aufgeben? 20kg Hühnerbrust, 10kg Kartoffeln, 5L Olivenöl?"
- Detects churn signals: declining order frequency, shrinking basket size, shift to cheaper products
- Alerts the field rep with context: "Customer X is at risk. Order frequency down 40% over 4 weeks. Last complaint: late delivery on 12 Feb."

**Why this is our #2 wedge:**
- This is a **greenfield opportunity** — nobody is doing this well. Plato does sales intelligence for large distributors; nobody does proactive retention for the mid-market.
- Directly protects revenue, not just saves cost. Easy to demonstrate ROI.
- Minimal integration needed — just historical order data.

##### 3. Smart Procurement (Upstream Ordering to Suppliers)
**Current state:** Procurement team of 3–15 people manually evaluates 50–300 suppliers. Purchase orders go out via phone, email, fax. Price comparison is manual and labour-intensive. Compliance tracking (certifications, lot traceability) is in paper files.

**What our agent does:**
- Monitors inventory levels + incoming customer orders + demand forecasts
- Auto-generates purchase orders when restock triggers hit
- Compares suppliers on price, quality history, delivery reliability, and certifications
- Sends POs via email to suppliers (or integrates with EDI where available)
- Tracks supplier performance over time

**Why this is our #3 wedge:**
- Procurement is where margin is made or lost. A 2–5% reduction in COGS on a €50M wholesaler = €1–2.5M/year.
- Plato doesn't do procurement (sales only). Choco doesn't do procurement (ordering only). This is our unique angle.

---

#### TIER 2 — "Build If Time Allows" (High impact, but more complex)

##### 4. Order Confirmation & Modification
- Auto-confirm orders with line-by-line detail via WhatsApp/email
- AI-powered substitution suggestions when items are out of stock
- Self-service modification window for customers

##### 5. Invoicing & Payment Intelligence
- Predict which customers will pay late
- Send proactive payment reminders
- Auto-match incoming payments to invoices
- Intelligent dunning (adjust tone by customer value)

##### 6. Catalogue & Dynamic Pricing
- Real-time personalised digital catalogue per customer
- AI-driven pricing recommendations (margin targets × demand elasticity × competition)

---

#### TIER 3 — "Not for Hackathon" (Important but requires deep integration)

| Touchpoint | Why defer |
|------------|-----------|
| Customer onboarding | Low frequency; requires credit bureau integrations |
| Inventory management | Requires WMS/ERP integration |
| Warehouse picking | Hardware-dependent (scanners, etc.) |
| Delivery & route optimisation | Requires fleet telematics integration |
| Returns & credits | Requires driver mobile app |
| Reporting & analytics | Foundational but not a wedge differentiator |

---

## Part 2: The Interaction Model

### How does the agent actually interact with users?

```
                    CUSTOMER SIDE                              WHOLESALER SIDE
                    ─────────────                              ───────────────

                    ┌─────────────┐                            ┌──────────────┐
                    │  WhatsApp   │───┐                   ┌───►│  Dashboard   │
                    └─────────────┘   │                   │    │  (Web App)   │
                    ┌─────────────┐   │   ┌───────────┐   │    └──────────────┘
                    │   Email     │───┼──►│           │───┤
                    └─────────────┘   │   │   AGENT   │   │    ┌──────────────┐
                    ┌─────────────┐   │   │   CORE    │   ├───►│  Email/      │
                    │   Phone     │───┤   │           │   │    │  WhatsApp    │
                    │  (voice)    │   │   └───────────┘   │    │  Alerts      │
                    └─────────────┘   │         │         │    └──────────────┘
                    ┌─────────────┐   │         │         │
                    │   Fax/PDF   │───┘         ▼         │    ┌──────────────┐
                    └─────────────┘       ┌───────────┐   └───►│  ERP         │
                                          │  Product   │       │  Integration │
                                          │  Catalogue │       └──────────────┘
                                          │  + Order   │
                                          │  History   │       ┌──────────────┐
                                          └───────────┘       │  Supplier    │
                                                               │  PO Emails   │
                                                               └──────────────┘
```

### Key design principle: NO NEW TOOL FOR THE CUSTOMER

The customer (restaurant chef) keeps using WhatsApp, email, and phone. They never download an app or log into a portal. The agent is invisible to them — they just notice that orders get confirmed faster, mistakes go down, and someone proactively reminds them to reorder.

The **wholesaler** gets a dashboard to:
- See all orders (auto-processed + flagged for review)
- Monitor customer health scores
- Review procurement suggestions
- Override agent decisions

---

## Part 3: Tech Stack Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION LAYER                          │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Email    │  │ WhatsApp │  │ Voice    │  │ PDF/Image     │  │
│  │ Webhook  │  │ Business │  │ (Twilio) │  │ Upload        │  │
│  │ (IMAP/   │  │ Cloud    │  │          │  │               │  │
│  │  webhook)│  │ API      │  │          │  │               │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬────────┘  │
│       │              │             │               │            │
│       └──────────────┴──────┬──────┴───────────────┘            │
│                             ▼                                   │
│                   ┌─────────────────┐                           │
│                   │ Message Router  │                           │
│                   │ & Normaliser    │                           │
│                   └────────┬────────┘                           │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    ORCHESTRATOR AGENT                     │  │
│  │            (Claude API — tool use / agentic)              │  │
│  │                                                           │  │
│  │  Determines intent → routes to specialist agent:          │  │
│  │                                                           │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │  │
│  │  │ Order Parser │ │ Reorder      │ │ Procurement      │  │  │
│  │  │ Agent        │ │ Nudge Agent  │ │ Agent            │  │  │
│  │  │              │ │              │ │                   │  │  │
│  │  │ • Parse NL   │ │ • Pattern    │ │ • Monitor stock  │  │  │
│  │  │ • Match SKUs │ │   detection  │ │ • Compare prices │  │  │
│  │  │ • Flag issues│ │ • Churn risk │ │ • Generate POs   │  │  │
│  │  │ • Confirm    │ │ • Auto-nudge │ │ • Track delivery │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                              │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Product Catalogue│  │ Order History    │  │ Customer     │  │
│  │                  │  │                  │  │ Profiles     │  │
│  │ • SKUs           │  │ • Past orders    │  │ • Preferences│  │
│  │ • Prices (per    │  │ • Frequencies    │  │ • Pricing    │  │
│  │   customer)      │  │ • Seasonal       │  │ • Risk score │  │
│  │ • Stock levels   │  │   patterns       │  │ • Contact    │  │
│  │ • Suppliers      │  │                  │  │   channels   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ Supplier         │  │ Conversation     │                    │
│  │ Directory        │  │ Memory           │                    │
│  │                  │  │                  │                    │
│  │ • Products       │  │ • Per-customer   │                    │
│  │ • Lead times     │  │   context        │                    │
│  │ • Price history  │  │ • Preferences    │                    │
│  │ • Reliability    │  │ • Past issues    │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                 │
│                    PostgreSQL / SQLite                           │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                              │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ WhatsApp     │  │ Email        │  │ Wholesaler Dashboard  │ │
│  │ Replies      │  │ Replies      │  │ (Next.js web app)     │ │
│  │              │  │              │  │                       │ │
│  │ • Order      │  │ • Order      │  │ • Order queue         │ │
│  │   confirm    │  │   confirm    │  │ • Flagged items       │ │
│  │ • Reorder    │  │ • Reorder    │  │ • Customer health     │ │
│  │   nudge      │  │   nudge      │  │ • Procurement recs    │ │
│  │ • Substitut. │  │ • POs to     │  │ • Agent activity log  │ │
│  │   suggestion │  │   suppliers  │  │                       │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

### Concrete Tech Choices for Hackathon (30h)

| Layer | Technology | Why this choice |
|-------|-----------|----------------|
| **LLM** | Claude API (claude-sonnet-4-6) | Best tool-use / agentic capabilities; fast; cost-effective for high volume |
| **Agent Framework** | Python + Claude tool-use (native) | Simpler than LangGraph for hackathon; Claude's native tool use is sufficient for multi-step workflows |
| **Backend** | FastAPI (Python) | Lightweight, async-native, fast to prototype |
| **Database** | SQLite (→ PostgreSQL in prod) | Zero setup; sufficient for demo; easy to seed with mock data |
| **Frontend** | Next.js + Tailwind CSS | Fast to build a polished dashboard; SSR for real-time updates |
| **Email ingestion** | Nylas API or simple IMAP polling | Nylas is cleaner but IMAP works for hackathon |
| **WhatsApp** | Twilio WhatsApp Sandbox | Free for development; simulates real WhatsApp interactions |
| **Voice** | Twilio Voice + Whisper API | Twilio receives calls; Whisper transcribes; Claude parses |
| **Image/PDF parsing** | Claude Vision (multimodal) | Can read handwritten order lists, fax images, PDF order forms directly |
| **Outbound messages** | Twilio (WhatsApp + SMS) + SMTP (email) | Reply on the same channel the order came from |
| **Deployment** | Vercel (frontend) + Railway/Fly.io (backend) | Fast deployment, free tiers available |
| **Scheduling** | APScheduler or Celery Beat | For periodic tasks: reorder nudges, procurement checks, churn scanning |

---

### Data Model (Simplified for MVP)

```sql
-- Core entities
customers (id, name, type, contact_email, contact_phone, contact_whatsapp,
           preferred_channel, delivery_address, payment_terms, credit_limit,
           health_score, created_at)

products  (id, name, name_de, sku, category, unit, price_default,
           stock_quantity, reorder_threshold, shelf_life_days,
           supplier_id, created_at)

suppliers (id, name, contact_email, contact_phone, lead_time_days,
           reliability_score, created_at)

-- Customer-specific pricing
customer_prices (customer_id, product_id, price, valid_from, valid_to)

-- Orders (from customers)
orders    (id, customer_id, channel, raw_message, status,
           created_at, confirmed_at, processed_by)
           -- channel: email | whatsapp | phone | fax | web
           -- status: received | parsed | confirmed | flagged | fulfilled

order_items (id, order_id, product_id, quantity, unit_price,
             matched_confidence, original_text, substitution_for)

-- Purchase orders (to suppliers)
purchase_orders (id, supplier_id, status, total_amount,
                 created_at, sent_at, expected_delivery)

po_items  (id, purchase_order_id, product_id, quantity, unit_cost)

-- Agent activity log
agent_actions (id, agent_type, action, entity_type, entity_id,
               details_json, confidence, human_reviewed, created_at)
               -- agent_type: order_parser | reorder_nudge | procurement

-- Conversation memory (per customer)
conversations (id, customer_id, channel, direction, message_text,
               parsed_intent, created_at)

-- Order patterns (precomputed for reorder nudges)
order_patterns (customer_id, product_id, avg_interval_days,
                avg_quantity, last_order_date, next_expected_date,
                confidence)
```

---

### Agent Design: How the Three Agents Work

#### Agent 1: Order Parser

```
INPUT:  Raw message (email body, WhatsApp text, voice transcript, image)
        + Customer context (if identifiable from phone/email)

STEPS:
1. Identify customer (match email/phone to customer record)
2. Extract order intent (is this an order, inquiry, complaint, or chat?)
3. Parse items: for each line/mention, extract:
   - Product name (fuzzy match to catalogue)
   - Quantity + unit
   - Delivery date preference
4. Validate:
   - Is this quantity plausible? (compare to historical orders)
   - Is the product in stock?
   - Is the price within the customer's agreed terms?
5. If confidence > threshold:
   → Auto-confirm, send confirmation via same channel, push to order queue
6. If confidence < threshold OR anomaly detected:
   → Flag for human review, explain what's uncertain

OUTPUT: Structured order + confirmation message + any flags

TOOLS the agent uses:
- search_product_catalogue(query) → fuzzy SKU match
- get_customer_history(customer_id) → past orders for context
- check_inventory(product_id) → current stock
- get_customer_pricing(customer_id, product_id) → correct price
- send_message(customer_id, channel, message) → confirmation
- create_order(customer_id, items[]) → push to system
- flag_for_review(order_id, reason) → human review queue
```

#### Agent 2: Reorder Nudge Agent (runs on schedule)

```
INPUT:  All customer order patterns + current date

STEPS:
1. Scan order_patterns table for customers past their expected reorder date
2. For each overdue customer:
   a. Check: have they ordered via another channel we might have missed?
   b. Calculate risk level (1 day late = gentle nudge; 7 days = churn alert)
   c. Generate personalised reorder suggestion:
      "Hallo Chef Meyer, Ihre übliche Dienstagsbestellung steht noch aus.
       Sollen wir folgendes aufgeben?
       - 20kg Hühnerbrust (€4.20/kg)
       - 10kg Kartoffeln (€1.10/kg)
       - 5L Olivenöl extra vergine (€8.90/L)
       Einfach mit 'Ja' bestätigen oder Änderungen durchgeben."
   d. Send via customer's preferred channel
3. For high-risk customers (declining frequency/value over 4+ weeks):
   → Alert field rep via email/dashboard with full context

OUTPUT: Nudge messages sent + churn alerts created

TOOLS:
- get_overdue_customers(date) → list of customers past reorder window
- get_reorder_suggestion(customer_id) → typical basket
- send_message(customer_id, channel, message) → nudge
- create_alert(type, customer_id, details) → dashboard alert
```

#### Agent 3: Procurement Agent (runs on schedule + triggered by orders)

```
INPUT:  Current inventory + incoming orders + supplier catalogue

STEPS:
1. Calculate net demand: (current stock) - (committed orders) - (safety stock)
2. For products below reorder threshold:
   a. Identify eligible suppliers (product availability, lead time, certifications)
   b. Compare: price, quality score, delivery reliability
   c. Factor in MOQs (minimum order quantities) and volume discounts
   d. Generate optimal purchase order(s)
3. Present PO drafts to procurement manager via dashboard
4. On approval: send PO to supplier via email
5. Track: expected delivery dates, actual arrivals, discrepancies

OUTPUT: Draft POs + supplier emails (on approval)

TOOLS:
- get_inventory_status() → all products below threshold
- get_committed_orders() → orders not yet fulfilled
- get_suppliers_for_product(product_id) → eligible suppliers
- compare_suppliers(product_id, quantity) → ranked options
- generate_purchase_order(supplier_id, items[]) → draft PO
- send_purchase_order(po_id) → email to supplier
```

---

### Hackathon Scope vs. Production Scope

| Capability | Hackathon (30h) | Production |
|------------|-----------------|------------|
| **Order channels** | Email + WhatsApp simulator | + Voice (Twilio) + Fax (eFax API) + Web portal |
| **Product catalogue** | ~200 mock SKUs (beverages, dairy, meat, produce, dry goods) with German names | Full ERP integration, 5,000–25,000 SKUs |
| **Customer data** | 10–20 mock customers with order histories | Full ERP customer master |
| **Agent confidence** | Fixed threshold (e.g., 0.85) | Adaptive per customer; learning from corrections |
| **Procurement** | 5 mock suppliers; manual approval | EDI integration; auto-approval for routine POs |
| **Dashboard** | Order queue + flags + customer health | Full analytics, reporting, team management |
| **Authentication** | None (demo mode) | SSO, role-based access |
| **Deployment** | Local + demo URL | Multi-tenant SaaS |
| **Language** | German + English | + French, Dutch, Italian, Polish |

---

### What to Demo (The "Wow" Moment)

**Scenario: Monday morning at Rheinfood, Cologne**

1. **[22:30 Sunday]** Chef Meyer sends WhatsApp voice message: "Hallo, ich brauch für morgen 20 Kilo Hühnerbrust, 10 Kilo Kartoffeln, und das übliche Olivenöl. Ach ja, und habt ihr noch die Tomaten aus Italien?"

2. **[22:30 Sunday]** Agent transcribes, parses, matches to SKUs, checks stock, finds Italian tomatoes are low → suggests Spanish alternative. Sends confirmation:
   "Bestellung erfasst, Chef Meyer:
   ✓ 20kg Hühnerbrust (€4.20/kg) — €84.00
   ✓ 10kg Kartoffeln festkochend (€1.10/kg) — €11.00
   ✓ 5L Olivenöl extra vergine (€8.90/L) — €44.50
   ⚠️ Italienische Strauchtomaten nur noch 3kg auf Lager.
      Alternative: Spanische Rispentomaten (€2.80/kg)?
   Lieferung: Montag vor 10:00 Uhr"

3. **[06:00 Monday]** Inside sales team arrives. Dashboard shows: 47 orders auto-processed overnight. 3 flagged for review (one quantity anomaly, one new customer, one out-of-stock item with no substitute).

4. **[06:15 Monday]** Procurement agent has already drafted POs for 5 suppliers to replenish Italian tomatoes, chicken breast, and 3 other items approaching threshold. Procurement manager reviews and approves with one click.

5. **[10:00 Tuesday]** Restaurant Zum Löwen hasn't placed their usual Tuesday order. Agent sends nudge: "Hallo Chef Schmidt, Ihre übliche Bestellung steht noch aus. Sollen wir aufgeben: 15kg Schweinefilet, 8kg Zwiebeln, 20L Speiseöl?"

---

## Sources

- [Choco OrderAgent](https://choco.com/us/orderagent) — AI order processing for food distributors
- [Orderlion AI Inbox](https://www.orderlion.com/en) — Multi-channel order conversion
- [kollex](https://www.kollex.de/) — Digital ordering for beverage wholesale
- [metasfresh ERP](https://metasfresh.com/) — Open-source ERP for food & wholesale
- [CSB-System](https://www.csb.com/en/industries/food-beverages) — ERP for food & beverages
- [GWS](https://gws.ms/en/food-wholesale/) — ERP for food wholesale
- [addHelix](https://www.addhelix.com/en/tourenplanung-fuer-grosshandel-lebensmittel-und-getraenkelogistik/) — Route planning for food wholesale
- [Twilio WhatsApp API](https://www.twilio.com/whatsapp) — WhatsApp Business integration
- [Twilio Voice + Whisper](https://www.twilio.com/voice) — Voice ingestion + transcription
