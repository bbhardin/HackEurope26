# Product Improvements & System Enhancements

## 1. Health Score Clarification for User

1. The app currently shows a health score which may depend on order frequency and anomalies to regular orders.
2. This may need to be clarified to the user or be supplemented with greater reason as to why the health score is lower.
3. Alternatively, it can simply be a description of anomalies to the regular customer behaviour with a severity rating, more like a traffic light.

---

## 2. Fulfilment Differential from Order Accept

1. Currently, the user can only accept/reject an order. This then triggers a response that does the following:
   1. Send confirmation to customer about order receipt.
   2. Send confirmation of order fulfilment to customer.
2. This leads to the following problem:
   - The order will automatically be allocated to the “Confirmed” tab of the Order Queue.
   - No “Fulfilled” tab exists.
   - An order cannot be fulfilled in the system for the User.
   - The order is automatically confirmed and delivery scheduled automatically.
3. Required changes:
   1. A confirmation response which:
      - Triggers a confirmation message to the customer.
      - Moves an order from **Pending → Confirmed** in the Order Queue.
   2. A separate delivery response which:
      - Triggers a delivery message to the customer.
      - Moves an order from **Confirmed → Fulfilled** in the Order Queue.

---

## 3. Manual Response Option for User

1. Currently, we have an automatic response option from User to Customer based on the accept/reject option.
2. However, a User may want to respond via a manual response to the Customer.
3. The same should apply to the fulfilment option above.

---

## 4. Clarify Flagged Status in Order Queue

1. Currently the Order Queue has a flagged tab.
2. We need to:
   - Know why an order may be flagged, and/or
   - Allow the user to define what would flag an order.
3. This needs to be clear to the user as it is not entirely intuitive.

---

## 5. Total Items to Be Fulfilled Overview

1. Currently, each order has an overview of the goods demanded/ordered.
2. This is very helpful for each individual order.
3. However, a wholesaler would benefit from:
   - An aggregate overview of all items on order.
   - This would support stock management coordination.
4. Implementation suggestion:
   - Create an overview tab in the sidebar.

---

## 6. Message API Integration

1. Currently the message API does not work.
2. This needs to be fixed.

---

## 7. Full Units of Items Only (or Continuous Units)

1. Currently, orders allow partial units of goods.
2. This makes sense for continuous units.
3. However, it does not make sense for indivisible goods (e.g., bags).
4. This needs to be standardised.

---

## 8. SKU Catalog Discrepancy

1. Customers’ messages are currently translated directly into orders.
2. There may be discrepancies between:
   - What goods are requested, and
   - What goods and units a wholesaler can offer.
3. It should be possible to:
   - Clarify with the customer which SKUs and quantities are available.
   - Allow messaging back and forth before final confirmation.
4. Orders should only be fixed once they have been confirmed.

---

## 9. Manual Override of Order Details

1. A user may want to manually edit an order.
2. Reasons may include:
   - Communication outside linked channels.
   - External events affecting order details (e.g., running out of stock).

---

## 10. Multi-Channel Communication Tracking

1. Currently, the user can only interact with customers via the platform.
2. The system should allow tracking of communication via alternative channels.
   - Example: WhatsApp conversations.
3. The application should:
   - Recognise meaningful conversation related to order edits.
   - Automatically integrate relevant changes into the application.