# Agentic AI Hackathon Demo – Architecture Flow

## 1. Message Ingress (WhatsApp Gateway)
Customer message arrives through the messaging gateway and is handed off to the system.

## 2. Customer Identification (Phone Number String Check)
Match the sender’s phone number to identify the customer and resolve the customer identifier.

## 3. Context Retrieval (customer.txt)
Retrieve the customer’s context file (e.g., `customer.txt`) from storage using the resolved customer identifier.

## 4. Language Understanding (OpenAI LLM + Customer Context)
Send the raw incoming message together with the retrieved `customer.txt` content to the OpenAI LLM.

The model:
- Classifies the intent  
- Extracts structured data  

Possible intents:
- `repeat_order`
- `remind_last_order`

---

# Intent Routing (Agent Behavior Switch)

## A. If Intent = `remind_last_order`

1. LLM generates a summary of last week’s order using `customer.txt`.
2. System immediately sends the reminder message back to the customer.
3. No dashboard update required.
4. Flow ends.

---

## B. If Intent = `repeat_order`

### 5. Decision / Orchestrator
Apply demo assumption (infinite stock).  
Prepare a proposed order using structured LLM output.

### 6. Order Event Creation (Pending State)
Create a “pending order” event containing:
- Customer ID  
- Product  
- Quantity  
- LLM reasoning  

### 7. Dashboard Updater (UI Backend)
Update the dashboard to show:
- Proposed order details  
- Updated total orders for product X for next week (including this pending order)  
- Order status = **Pending Confirmation**

### 8. Frontend Display with Approval Control
The UI displays the proposed order with two buttons:

- **Yes**
- **No**

### 9. Human Confirmation Step
- If **Yes** is clicked → Order status changes to **Confirmed**
- If **No** is clicked → Call empty placeholder method (no action for now; reserved for future logic)

### 10. Outbound Confirmation Message (Only After Yes)
Only when **Yes** is clicked, generate and send the WhatsApp confirmation:

> “Order for X product of XX number is placed.”

---

## 11. Audit & Trace Store
Persist:
- Incoming message  
- `customer.txt` snapshot used  
- LLM input/output  
- Intent classification  
- Human confirmation decision (if applicable)  
- Final order state  

---

## 12. Monitoring & Error Handling
Track:
- System activity  
- Lookup failures  
- LLM failures  
- Message delivery issues  
