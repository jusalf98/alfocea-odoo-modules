Connects the Alfocea vendor subscriptions with the purchase orders, in both directions.

**From purchase orders to subscriptions.** When a purchase order is confirmed (directly or after its approval), every line whose product has a **Vendor Subscription Plan** creates and starts a vendor subscription for the order vendor:

- One subscription per plan, with the subscription lines of the order (product, description, quantity and discounted price in the company currency).
- If the vendor already has an open subscription (draft, trial, active or paused) with that plan **and that product**, the quantity is added to it.
- A product the vendor does not have yet creates a new subscription, unless the plan has **One Subscription per Partner** enabled: then it is added as a new line to the existing one.
- The order is only linked to the subscriptions that contain its products.
- Cancelling the order reverts what it changed in the subscriptions.
- When confirming from the form an order that changes existing subscriptions, a wizard shows what they already have and what the order adds, with three options: **Confirm and Add**, **Confirm without Adding** (the existing subscriptions are not changed; new ones are still created) and **Cancel**.
- The confirmed order covers the first period, so the first renewal is due one period later. With a trial plan, the order is paid to the vendor, so it covers the first period after the trial.
- The vendor subscription plan is a different field from the (customer) subscription plan of the core module: a product can be sold with a plan and purchased without one, and the other way around.
- The subscriptions are created as superuser, so buyers don't need any subscription access right.

**From subscriptions to purchase orders.** A daily scheduled action creates the renewal purchase orders of the vendor subscriptions renewed with purchase orders, when their next invoice date has been reached:

- One purchase order per period, with the subscription lines and prices, and the period dates in the line descriptions.
- Missed periods are caught up, and no period starting after the subscription end date is ordered.
- The renewal orders keep the buyer of the order that created the subscription.
- Each plan decides whether its renewal purchase orders are confirmed automatically or left as requests for quotation (**Confirm Renewal Purchase Orders**).

Smart buttons link the purchase orders and their subscriptions in both directions.
