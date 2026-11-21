Connects the Alfocea subscriptions with the sale orders, in both directions.

**From sale orders to subscriptions.** When a quotation is confirmed, every line whose product has a **Subscription Plan** creates and starts a customer subscription for the order customer:

- One subscription per plan, with the subscription lines of the order (product, description, quantity and discounted price in the company currency).
- If the customer already has an open subscription (draft, trial, active or paused) with that plan **and that product**, the quantity is added to it.
- A product the customer does not have yet creates a new subscription, unless the plan has **One Subscription per Partner** enabled: then it is added as a new line to the existing one.
- The order is only linked to the subscriptions that contain its products.
- Cancelling the order reverts what it changed in the subscriptions.
- When confirming from the form an order that changes existing subscriptions, a wizard shows what they already have and what the order adds, with three options: **Confirm and Add**, **Confirm without Adding** (the existing subscriptions are not changed; new ones are still created) and **Cancel**.
- The confirmed order covers the first period, so the first renewal is due one period later.
- **Free trial:** the quotation lines in trial are shown in green. A quotation line whose product starts a new subscription with a trial plan gets a 100% discount and a note in its description ("Free trial: 7 days. Then billed every 1 Month(s)."). The customer pays nothing now: the subscription keeps the real price and its first invoice is at the end of the trial. Buying the product again, or adding it to an existing subscription, is never a trial. Only quotations are flagged: confirmed orders keep their discounts.
- The subscriptions are created as superuser, so salesmen don't need any subscription access right to confirm orders.

**From subscriptions to sale orders.** A daily scheduled action creates the renewal sale orders of the customer subscriptions whose next invoice date has been reached:

- One sale order per period, with the subscription lines and prices, and the period dates in the line descriptions (in the customer language).
- Missed periods are caught up, and no period starting after the subscription end date is ordered.
- The renewal orders keep the salesperson and sales team of the order that created the subscription.
- Each plan decides whether its renewal orders are confirmed automatically or left as quotations (**Confirm Renewal Orders**).
- An error in one subscription is logged and does not block the renewal of the others.

Smart buttons link the sale orders and their subscriptions in both directions.
