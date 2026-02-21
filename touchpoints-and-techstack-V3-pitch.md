# The Wholesaler's AI Agent — Pitch & Story

## The One-Liner

An AI agent that lives inside your wholesaler's WhatsApp — it reads every customer order, structures it, and holds it for your approval. No new tools for your customers. No behaviour change. Just faster, smarter order processing.

---

## The Problem

European food & drink wholesaling is a **€2 trillion market** with 414,000 businesses. It runs on phone calls, WhatsApp messages, and gut feeling.

**Here's a typical day at a mid-size wholesaler (50 employees, €50M revenue):**

- Orders arrive around the clock — WhatsApp messages from chefs at 10pm, voicemails at midnight, emails at 5am
- A team of inside sales staff spend their entire morning **manually transcribing** these messages into the ERP
- Error rate: 1–3%. On a €50M business, that's €500K–1.5M in mis-shipped orders per year
- When a regular customer forgets to order, nobody notices until it's too late
- When a sales rep leaves, their customer relationships walk out the door

**The result:** Wholesalers spend their most expensive resource (people) on their lowest-value task (data entry), while high-value tasks (customer retention, relationship building) get no attention at all.

---

## The Solution

We place an AI agent between the customer and the wholesaler. The customer keeps using WhatsApp — nothing changes for them. The agent does the heavy lifting.

### How It Works (60-Second Version)

```
  CHEF                          OUR AGENT                        WHOLESALER
   │                               │                                │
   │  "Hi, need 20kg chicken,      │                                │
   │   10kg potatoes, and the      │                                │
   │   usual olive oil"            │                                │
   │ ─────────────────────────────►│                                │
   │          (WhatsApp)           │  Parses message                │
   │                               │  Matches to catalogue          │
   │                               │  Checks order history          │
   │                               │  Builds structured order       │
   │                               │ ──────────────────────────────►│
   │                               │     (Dashboard: "Approve?")    │
   │                               │                                │
   │                               │                    clicks YES  │
   │                               │◄──────────────────────────────│
   │                               │                                │
   │  "Order confirmed:            │                                │
   │   20kg chicken (€84)          │                                │
   │   10kg potatoes (€11)         │                                │
   │   5L olive oil (€44.50)       │                                │
   │   Total: €139.50              │                                │
   │   Delivery: Mon before 10am"  │                                │
   │◄─────────────────────────────│                                │
   │          (WhatsApp)           │                                │
```

### Three Core Capabilities

**1. Intelligent Order Intake**
Every WhatsApp message — text, voice note, photo of a handwritten list — is parsed into a clean, structured order. Fuzzy product matching handles the way chefs actually talk: "the usual cheese, but the big one" becomes Emmentaler 500g. Anomalies are flagged: "This customer usually orders 50 cases. They ordered 500 — typo?"

The wholesaler stays in control. Every order requires human approval before the customer gets a confirmation.

**2. Proactive Reorder Nudges**
The agent learns each customer's ordering rhythm. When The Oak Restaurant — which orders every Tuesday — hasn't ordered by Wednesday morning, the agent sends a gentle WhatsApp nudge: "Shall we place your usual order? 15kg pork tenderloin, 8kg onions, 20L cooking oil." One reply to confirm.

This catches revenue that would otherwise silently disappear. And when a customer's order frequency is declining over weeks, the agent flags it as a churn risk on the wholesaler's dashboard.

**3. Seamless Order Confirmation & Modification**
After approval, the customer gets a detailed WhatsApp confirmation with line items, prices, and delivery time. If they want to change something ("Actually, make it 30kg chicken"), they just reply. The agent re-parses and sends the update back for approval. No portals, no apps, no friction.

---

## The Architecture: One Agent Per Customer

This is our key differentiator in how we build it.

Rather than one monolithic AI processing all messages, we spin up a **dedicated agent per customer**. Each customer agent holds that customer's full context — their order history, typical basket, delivery schedule, conversation history, and preferences. It becomes an expert on that specific customer.

A **Wholesaler Orchestrator** coordinates across all customer agents, manages the dashboard, and handles the human approval flow.

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
- Each agent gets better at understanding its customer over time
- Context never leaks between customers
- The system scales naturally — adding a customer is just spawning a new agent
- If a sales rep leaves, the customer knowledge stays in the agent

---

## The Demo: Monday Morning at Rheinfood

**Sunday 22:30** — Chef Meyer sends a WhatsApp message: "Hi, I need for tomorrow 20kg chicken breast, 10kg potatoes, and the usual olive oil."

The agent (Meyer's dedicated agent) parses the message overnight: identifies the customer from the phone number, loads their context, matches products to the catalogue, and creates a structured order on the dashboard.

**Monday 06:00** — The sales team arrives. The dashboard shows:

- **Total pending order value: €1,247.80** across 12 orders parsed overnight
- All awaiting one-click confirmation
- 1 flagged anomaly: a customer ordered 500 units instead of their usual 50
- 1 unknown phone number flagged for review

The sales rep clicks **Yes** on Meyer's order. WhatsApp confirmation goes out instantly with line items, prices, and delivery time.

**Tuesday 10:00** — The Oak Restaurant hasn't placed their usual Tuesday order. The agent detects this and sends a nudge: "Shall we place your usual order?" Chef Davis replies "Yes." Done.

**What just happened:** A team that used to spend 3 hours every morning transcribing orders finished in 15 minutes. A customer who would have silently churned got a nudge and stayed. Zero new tools for anyone to learn.

---

## Why Us vs. the Competition

| | **Choco** | **Plato** | **Us** |
|---|---|---|---|
| **What they do** | Ordering platform + marketplace | AI sales intelligence for large distributors | AI agent inside existing WhatsApp |
| **Customer requirement** | Must move onto Choco's platform | Enterprise deployment (€100K+ ACV) | Zero behaviour change — keeps using WhatsApp |
| **Target** | All sizes (platform play) | Large distributors (€500M+) | Mid-size regional (€20M–200M, up to 50 employees) |
| **Approach** | Platform with AI bolted on | Analytics layer on ERP | Agent-native — AI is the product |
| **Procurement** | No | No | Not yet (future expansion) |
| **Funding** | $301M, $1.2B valuation | €12.2M Seed (Atomico) | Pre-seed |

**Our wedge:** We don't ask anyone to change how they work. The chef keeps using WhatsApp. The wholesaler gets a dashboard. The agent does everything in between. Choco requires platform adoption. Plato requires enterprise sales cycles. We require a WhatsApp number and a product catalogue.

---

## Market Opportunity

- **European F&B wholesaling:** ~€2 trillion, 414,000 businesses
- **Our beachhead:** Mid-size regional wholesalers in DACH (Germany, Austria, Switzerland)
  - Too small for Plato's 6-figure ACVs
  - Too sophisticated for Choco's ordering layer
  - Decision-making is fast (owner-operated, weeks not quarters to deploy)
- **Target ACV:** €10K–25K/year
- **Land & expand:** Start with order intake (€500/mo) → add reorder nudges → add invoicing → add demand prediction

### Unit Economics (per wholesaler)

| Metric | Value |
|--------|-------|
| Inside sales staff replaced/augmented | 2–4 FTEs |
| Salary per FTE (DACH) | €40K–55K/year |
| Our annual cost to wholesaler | €10K–25K/year |
| **ROI for wholesaler** | **4–10x** |
| Revenue at risk from churn (recovered) | 5–15% of top line |

---

## What We're Building at the Hackathon

In 30 hours, we're building a working demo that shows:

1. A customer sends a WhatsApp message with an order
2. Our agent parses it, matches products, and presents a structured order on a dashboard
3. The wholesaler approves with one click
4. The customer gets an instant WhatsApp confirmation
5. A customer who forgets to order gets a proactive nudge

**Tech:** Claude API (agentic), FastAPI backend, Next.js dashboard, Meta WhatsApp Business API, SQLite with mock data.

---

## The Ask

We're looking for:
- **Pre-seed funding** to build out the full product and onboard 5 pilot wholesalers in DACH
- **Introductions** to mid-size F&B wholesalers who are drowning in manual order processing
- **Feedback** on our agent architecture and go-to-market approach

---

## Team

[To be filled in]

---

## Sources

- [Choco — $301M raised, $1.2B valuation](https://choco.com/us/)
- [Plato — €12.2M Seed from Atomico, Feb 2026](https://www.eu-startups.com/2026/02/from-germany-for-the-world-plato-secures-e12-2-million-to-automate-sales-and-erp-workflows-in-distribution)
- [IBISWorld — European F&B Wholesaling: €2T market, 414K businesses](https://www.ibisworld.com/europe/industry/food-drink-wholesaling/200227/)
- [48% of food suppliers still rely on spreadsheets](https://www.anchorgroup.tech/blog/food-beverage-supply-chain-statistics)
- [Meta WhatsApp Business Platform](https://developers.facebook.com/docs/whatsapp/cloud-api)
