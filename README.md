
# Kuna — AI Order Agent for Food & Beverage Wholesalers

> *Built at HackEurope 2026 in 30 hours.*

**Kuna** is your wholesale AI agent to connect with customers using the channels they prefer. It reads every customer order, structures it instantly, and holds it for your one-click approval. No new tools for your customers. No behaviour change. Just faster, smarter order processing.

---

## The Problem

European food & drink wholesaling is a **€2 trillion market** with 414,000 businesses. It runs on phone calls, WhatsApp messages, and gut feeling.

A typical day at a mid-size wholesaler (50 employees, €50M revenue):
- Orders arrive around the clock — WhatsApp messages from chefs at 10pm, voicemails at midnight, emails at 5am
- Inside sales staff spend every morning **manually transcribing** messages into the ERP
- Error rate: 1–3%. On €50M revenue, that's **€500K–1.5M in mis-shipped orders per year**
- When a regular customer forgets to order, nobody notices until it's too late
- When a sales rep leaves, their customer relationships walk out the door

**The result:** Wholesalers spend their most expensive resource (people) on their lowest-value task (data entry), while high-value work — customer retention, relationship building — gets no attention at all.

---

## The Solution

```
  CHEF                          KUNA AGENT                       WHOLESALER
   │                               │                                │
   │  "Hi, need 20kg chicken,      │                                │
   │   10kg potatoes, and the      │                                │
   │   usual olive oil"            │                                │
   │──────────────────────────────►│                                │
   │         (WhatsApp)            │  Parses message                │
   │                               │  Matches to catalogue          │
   │                               │  Checks order history          │
   │                               │  Builds structured order       │
   |                               |  Determines confidence in query|
   |                               |  Confidence too low? Wait approval |
   │                               │───────────────────────────────►│
   │                               │    (Dashboard: "Approve?")     │
   │                               │                                │
   │                               │                   clicks YES   │
   │                               │◄─────────────────────────────-─│
   │                               │                                │
   │  "Order confirmed:            │                                │
   │   20kg chicken (€84)          │                                │
   │   10kg potatoes (€11)         │                                │
   │   5L olive oil (€44.50)       │                                │
   │   Total: €139.50              │                                │
   │   Delivery: Mon before 10am"  │                                │
   │◄──────────────────────────────│                                │
   │         (WhatsApp)            │                                │
```

---

## Features

### Intelligent Order Intake
Every WhatsApp message — text, photo of a handwritten list, image of a product — is parsed into a clean, structured order. Fuzzy product matching handles the way chefs actually talk: *"the usual cheese, but the big one"* maps to Emmentaler 500g. Anomalies are flagged automatically: *"This customer usually orders 50 cases. They just ordered 500 — typo?"*

The wholesaler stays in control. Every order requires human approval before the customer gets a confirmation.

### Proactive Reorder Nudges
The agent learns each customer's ordering rhythm. When The Oak Restaurant — which orders every Tuesday — hasn't placed an order by Wednesday morning, the agent sends a gentle WhatsApp nudge:
> *"Shall we place your usual order? 15kg pork tenderloin, 8kg onions, 20L cooking oil."*

One reply to confirm. Revenue that would have silently disappeared, recovered.

### Churn Risk Detection
When a customer's order frequency declines over consecutive weeks, the agent flags it as a churn risk on the wholesaler's dashboard — before the customer is lost.

### Conversation-Aware Context
Each customer agent maintains full conversation history. If the agent asks *"Shall I place your usual order?"* and the customer replies *"Yes"*, it correctly interprets the confirmation. Context carries across messages, exactly as it would with a human sales rep.

### Seamless Order Modification
After approval, the customer gets a detailed WhatsApp confirmation with line items, prices, and delivery time. If they want to change something (*"Actually, make it 30kg chicken"*), they just reply. The agent re-parses and submits the update for approval. No portals, no apps, no friction.

---

## Architecture: One Agent Per Customer

Rather than one monolithic AI processing all messages, Kuna spins up a **dedicated agent per customer**. Each agent holds that customer's full context — order history, typical basket, delivery schedule, conversation history, and preferences.

```
                    ┌─────────────────────────────┐
                    │   WHOLESALER ORCHESTRATOR    │
                    │                              │
                    │   • Dashboard management     │
                    │   • Human approval flow      │
                    │   • Cross-customer analytics │
                    └──────────┬───────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Customer Agent: │ │ Cust. Agent: │ │ Cust. Agent: │
    │ Chef Meyer      │ │ The Oak      │ │ Hotel Grand  │
    │                 │ │              │ │              │
    │ • Order history │ │ • Order hist │ │ • Order hist │
    │ • Preferences   │ │ • Preferences│ │ • Preferences│
    │ • Typical basket│ │ • Typ. basket│ │ • Typ. basket│
    │ • Conv. history │ │ • Conv. hist │ │ • Conv. hist │
    └─────────────────┘ └──────────────┘ └──────────────┘
```

**Why this matters:**
- Each agent improves at understanding its specific customer over time
- Context never leaks between customers
- The system scales naturally — adding a customer is just spawning a new agent
- If a sales rep leaves, the customer knowledge stays in the system

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI / Agents** | [Claude API](https://www.anthropic.com/) (claude-sonnet-4) with tool use & vision |
| **Backend** | Python 3.12, FastAPI, async/await throughout |
| **Frontend** | Next.js 15 (App Router), React, Tailwind CSS v4 |
| **Database** | SQLite (WAL mode) via Python `sqlite3` |
| **Messaging** | Meta WhatsApp Cloud API (Business Platform) |
| **Charting** | Recharts |
| **Deployment** | Uvicorn, ngrok (dev) |

---

## Project Structure

```
kuna/
├── backend/
│   ├── app/
│   │   ├── routers/          # FastAPI route handlers
│   │   │   ├── webhook.py    # WhatsApp webhook (inbound messages)
│   │   │   ├── orders.py     # Order management endpoints
│   │   │   ├── customers.py  # Customer profile endpoints
│   │   │   ├── simulate.py   # Demo simulation endpoints
│   │   │   └── ...
│   │   ├── customer_agent.py # Per-customer Claude agent (vision + tool use)
│   │   ├── orchestrator.py   # Wholesaler orchestrator & approval flow
│   │   ├── pipeline.py       # Inbound message processing pipeline
│   │   ├── whatsapp.py       # WhatsApp Cloud API client
│   │   ├── nudge_scheduler.py# Proactive reorder nudge engine
│   │   ├── crud.py           # Database access layer
│   │   └── seed.py           # Demo data seeder
│   └── .env.example
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx          # Overview dashboard
│       │   ├── orders/           # Order queue (approve/decline)
│       │   ├── customers/[id]/   # Customer profile + conversation + chart
│       │   ├── activity/         # Agent action log
│       │   └── alerts/           # Churn & anomaly alerts
│       └── components/
│           ├── Sidebar.tsx       # Navigation + dark/light mode toggle
│           └── Toast.tsx
└── data/
    └── demo.db                   # SQLite database
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- A [Meta WhatsApp Business](https://developers.facebook.com/docs/whatsapp/cloud-api) account
- An [Anthropic API key](https://console.anthropic.com/)

### 1. Clone & install backend

```bash
git clone https://github.com/your-org/kuna.git
cd kuna/backend
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

```env
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Meta WhatsApp Cloud API
META_WHATSAPP_TOKEN=your_permanent_system_user_token
META_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_chosen_verify_token

# Database
DATABASE_PATH=../data/demo.db
```

> **Note:** Use a [System User token](https://developers.facebook.com/docs/marketing-api/system-users) for `META_WHATSAPP_TOKEN` — temporary tokens expire every 24 hours.

### 3. Seed the database

```bash
cd backend
python -m app.seed
```

### 4. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Expose via ngrok (for WhatsApp webhooks)

```bash
ngrok http 8000
```

Configure your Meta webhook URL as:
```
https://<your-ngrok-url>/webhook
```

With verify token matching `WHATSAPP_VERIFY_TOKEN`, subscribed to the **messages** field.

### 6. Install & start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Demo Flow

**Sunday 22:30** — Chef Meyer sends a WhatsApp message:
> *"Hi, I need for tomorrow 20kg chicken breast, 10kg potatoes, and the usual olive oil."*

The agent parses the message overnight: identifies the customer from their phone number, loads their context, matches products to the catalogue, flags a quantity anomaly if needed, and creates a structured order on the dashboard.

**Monday 06:00** — The sales team opens the dashboard:
- **Total pending order value: €1,247.80** across 12 orders parsed overnight
- All awaiting one-click confirmation
- 1 flagged anomaly: a customer ordered 500 units instead of their usual 50
- 1 churn risk alert: Hotel Grand hasn't ordered in 3 weeks

The rep clicks **Approve** on Meyer's order. A WhatsApp confirmation goes out instantly with itemised prices and delivery time.

**Tuesday 10:00** — The Oak Restaurant hasn't placed their usual Tuesday order. The nudge engine detects this and sends:
> *"Shall we place your usual order? 15kg pork tenderloin, 8kg onions, 20L cooking oil."*

Chef Davis replies *"Yes."* Done. Order confirmed, no manual work required.

**What just happened:** A team that used to spend 3 hours every morning transcribing orders finished in 15 minutes. A customer who would have silently churned got a nudge and stayed. Zero new tools for anyone to learn.

---

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Overview** | KPI cards (pending, confirmed, fulfilled), recent orders, active alerts, demo controls |
| **Order Queue** | Tabbed view of all orders by status; one-click approve/decline with auto-WhatsApp confirmation |
| **Customers** | Customer list with health scores and order frequency |
| **Customer Profile** | Full conversation history, order history chart (by week/month), typical basket |
| **Activity Log** | Chronological log of every agent action |
| **Alerts** | Churn risks and anomaly flags with direct links to relevant customers/orders |

---

## Competitive Landscape

| | **Choco** | **Plato** | **Kuna** |
|---|---|---|---|
| **Approach** | Ordering platform + marketplace | AI sales intelligence for large distributors | AI agent inside existing WhatsApp |
| **Customer requirement** | Must adopt Choco's platform | Enterprise deployment (€100K+ ACV) | Zero behaviour change |
| **Target** | All sizes | Large distributors (€500M+) | Mid-size regional (€20M–200M) |
| **Funding** | $301M, $1.2B valuation | €12.2M Seed (Atomico) | Pre-seed |

**Our wedge:** We don't ask anyone to change how they work. The chef keeps using WhatsApp. The wholesaler gets a dashboard. Kuna does everything in between.

---

## Market Opportunity

- **European F&B wholesaling:** ~€2 trillion, 414,000 businesses
- **Beachhead:** Mid-size regional wholesalers in DACH (Germany, Austria, Switzerland)
  - Too small for Plato's 6-figure ACVs
  - Too sophisticated to simply adopt Choco's platform
  - Owner-operated — weeks, not quarters, to deploy
- **Target ACV:** €10K–25K/year
- **Land & expand:** Order intake → reorder nudges → invoicing → demand prediction

### Unit Economics (per wholesaler)

| Metric | Value |
|--------|-------|
| Inside sales staff augmented | 2–4 FTEs |
| Salary per FTE (DACH) | €40K–55K/year |
| Annual cost of Kuna | €10K–25K/year |
| **ROI for wholesaler** | **4–10x** |

---

## Sources

- [Choco — $301M raised, $1.2B valuation](https://choco.com/us/)
- [Plato — €12.2M Seed from Atomico, Feb 2026](https://www.eu-startups.com/2026/02/from-germany-for-the-world-plato-secures-e12-2-million-to-automate-sales-and-erp-workflows-in-distribution)
- [IBISWorld — European F&B Wholesaling: €2T market, 414K businesses](https://www.ibisworld.com/europe/industry/food-drink-wholesaling/200227/)
- [48% of food suppliers still rely on spreadsheets](https://www.anchorgroup.tech/blog/food-beverage-supply-chain-statistics)
- [Meta WhatsApp Business Platform](https://developers.facebook.com/docs/whatsapp/cloud-api)

---

*Built at HackEurope 2026.*
