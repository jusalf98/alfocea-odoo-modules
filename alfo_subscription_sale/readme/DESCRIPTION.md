Connects the Alfocea subscriptions with the sale orders, in both directions.

**From sale orders to subscriptions.** When a quotation is confirmed, every line whose product has a **Subscription Plan** creates and starts a customer subscription for the order customer:

- One subscription per plan, with the subscription lines of the order (product, description, quantity and discounted price in the company currency).
- If the customer already has an open subscription (draft, trial, active or paused) with that plan, no new subscription is created: the order is linked to the existing one.
- The confirmed order covers the first period, so the first renewal is due one period later (or at the end of the trial).
- The subscriptions are created as superuser, so salesmen don't need any subscription access right to confirm orders.

**From subscriptions to sale orders.** A daily scheduled action creates the renewal sale orders of the customer subscriptions whose next invoice date has been reached:

- One sale order per period, with the subscription lines and prices, and the period dates in the line descriptions (in the customer language).
- Missed periods are caught up, and no period starting after the subscription end date is ordered.
- The renewal orders keep the salesperson and sales team of the order that created the subscription.
- Each plan decides whether its renewal orders are confirmed automatically or left as quotations (**Confirm Renewal Orders**).
- An error in one subscription is logged and does not block the renewal of the others.

Smart buttons link the sale orders and their subscriptions in both directions.
