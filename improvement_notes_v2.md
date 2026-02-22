# Product & UX Enhancements

## 1. Message Handling Improvements

1. Customers can send different types of messages to the wholesaler. Most are handled correctly, but some exceptions need improvement:

   1. If a message is order-related but unclear in content:
      - It should be sorted into the **Flagged** tab.
      - The user should be able to respond to clarify order details.
      - Once clarified, the message should be reclassified as:
        - A non-order-related message, or
        - A correctly specified order, or
        - An order still requiring clarification.

   2. If a non-order-related message is received:
      - It should **not** trigger an order workflow.
      - The user should still be alerted.
      - The user should be able to respond, including using pre-written messages.
      - The alert should appear in the alert sidebar panel.

   3. If an order references recurring orders (e.g., “the usual”):
      - The system should confirm interpretation with the customer (e.g., *“Can I confirm that by ‘the usual’ you mean XYZ?”*).
      - This increases order accuracy and reinforces the application’s core value proposition (reduced error rates through precision).

---

## 2. Order Queue Adjustment

- Delete the **Clarification** tab.
- Move all clarification-related cases into the **Flagged** tab.

---

## 3. Customer Sidebar Panel Improvements

1. Add a **search bar** to search by customer name.
2. Add **sorting options**, including:
   - Health status
   - Name
   - Order volume
3. Add **filtering options**:
   - Pending orders
   - Confirmed orders
   - Other order states
4. Allow switching between:
   - Tile view
   - List view

---

## 4. Product Catalog Sidebar Panel

Create a new sidebar panel called **“Product Catalog”** that:

- Lists all products offered by the wholesaler.
- Allows:
  - Adding products
  - Deleting products
  - Editing product prices

---

## 5. Intelligent Manual Messaging

Wherever manual messages can be sent:

- Pre-fill the text field with a suggested message.
- Allow easy override.
- Where multiple message types are possible:
  - Provide multiple suggested options.
- Implement this intelligently with agent-like assistance.

---

## 6. Activity Log Improvements

In the activity log sidebar:

- Replace the “entity” column.
- Each activity should display:
  - Customer name (if applicable)
  - Order number (if applicable)
- Leave empty if not relevant.

---

## 7. Nudge Trigger Scan Redesign

Instead of automatically sending nudges:

- Highlight customers in the customer tab who may need a trigger.
- Indicate why a trigger is recommended.
- In tile view:
  - Provide a shortcut to send a trigger.
- In expanded customer profile view:
  - Provide suggested message options.
  - Allow manual override.

---

## 8. Dashboard Interactivity Improvements

The dashboard is strong but should become more interactive:

1. Top tiles should link directly to relevant Order Queue tabs.
2. Order lists should be clickable:
   - Clicking an order opens the expanded order view.
3. Active alerts should include suggested actions.
   - Example:
     - Incoming order → “Review order” → opens Pending tab.

---

## 9. More Agentic User Experience

The application should feel more agent-driven:

- Provide subtle confirmation pop-ups when actions occur (e.g., order confirmed).
- In chat:
  - Indicate states like “Awaiting customer response.”
- Adjust UI language to be more action-oriented and agent-like.
- Consider UI reorganisation to better highlight agent features.

---

## 10. Image Input Processing

Customers may send images (e.g., handwritten orders).

The system should:

- Parse image content.
- Match it to customer context.
- Process it similarly to structured text input.
- Save images within the customer profile.
- Reflect them in order history.

---

## 11. WhatsApp Customer Integration

WhatsApp numbers have been integrated and should be reflected in the system.

Create customer profiles with order context for:

1. **+44 7460 880940** – Mantas  
2. **+1 (812) 801-7698** – Ben  

These customers should:
- Be linked to the wholesaler.
- Be able to send messages via WhatsApp into the application.

On the flipside, we have a number representing the wholesaler. So any message sent from the application should automatically trigger a message from that number's WhatsApp to be sent to a customer number (the ones referenced above). The number for the wholsealer is:

- **+49 170 3478722** – Mads

---

## 12. Automatic Customer Profile Creation

When a new customer messages the application:

- Automatically create a customer profile using information in the message.
- Profile creation should trigger follow-up activity, such as:
  - Sending a welcome message.
- Additional automated actions can be configurable by the user.