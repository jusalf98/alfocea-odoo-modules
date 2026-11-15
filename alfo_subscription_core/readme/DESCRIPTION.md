Core module of the Alfocea subscription suite. It manages both the subscriptions you sell to your customers and the ones you contract with your vendors. It adds:

- **Subscription plans**: billing periodicity (days, weeks, months or years), interval and free trial days. Plans are shared by both kinds of subscriptions.
- **Subscription contracts** of two types:
  - **Customer subscriptions** (`SUB/` reference): the line prices come from the product sales price.
  - **Vendor subscriptions** (`PSUB/` reference): the line prices come from the vendor pricelist of the product, or from its cost if the vendor has no price.
- Each contract has a partner, a plan, start and end dates, a next invoice date, product lines and lifecycle states (draft, trial, active, paused, cancelled and expired).
- A daily scheduled action that moves finished trials to active and finished contracts to expired.
- Two security groups: *Subscriptions / User* and *Subscriptions / Administrator*.

Invoicing, sales and portal features are provided by other modules of the suite.
