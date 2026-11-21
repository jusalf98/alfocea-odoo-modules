Core module of the Alfocea subscription suite. It manages both the subscriptions you sell to your customers and the ones you contract with your vendors. It adds:

- **Subscription plans**: billing periodicity (days, weeks, months or years), interval and free trial days. Plans are shared by both kinds of subscriptions.
- **Subscription contracts** of two types:
  - **Customer subscriptions** (`SUB/` reference): the line prices come from the product sales price.
  - **Vendor subscriptions** (`PSUB/` reference): the line prices come from the vendor pricelist of the product, or from its cost if the vendor has no price.
- Each contract has a partner, a plan, start and end dates, a next invoice date, product lines and lifecycle states (draft, trial, active, paused, cancelled and expired).
- A daily scheduled action that moves finished trials to active and finished contracts to expired.
- A **PDF report of the subscription** (Print menu), in the partner language: partner, plan, billing periodicity, status, dates, lines, total per period and terms and conditions.
- A **PDF report of the plan** (Print menu): billing, free trial, company, status, description, the open subscriptions using it and the total per period of the running ones, for customers and vendors.
- Both reports can be printed for several records at once from the list views (one page per record).
- **End Trial** (subscription administrators only): ends the free trial today, the subscription becomes active and its next invoice comes forward. The chatter records who ended it and the planned end.
- **Confirmation wizard** for the sale and purchase modules: when confirming an order from its form would change existing subscriptions (quantity added or product added), it shows what they already have and, in green, what the order adds, before confirming. **Confirm and Add** applies the changes; **Confirm without Adding** confirms the order without changing the existing subscriptions (those products are sold once, new subscriptions are still created, and the order chatter records it); **Cancel** leaves the order unconfirmed.
- **Cancelling an order reverts what it changed** in the subscriptions (sale and purchase modules): the quantities it added are subtracted, the lines it added are removed and a subscription it created is cancelled when no line is left. Renewal documents already created are not touched. Every change from an order is logged (tab *Changes from Orders*, administrators) and the chatter explains what was reverted.
- Two security groups: *Subscriptions / User* and *Subscriptions / Administrator*.

Invoicing, sales and portal features are provided by other modules of the suite.
