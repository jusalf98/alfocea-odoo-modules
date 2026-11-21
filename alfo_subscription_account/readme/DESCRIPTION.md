Invoices the Alfocea subscriptions directly, without sale or purchase orders.

A daily scheduled action creates, for every subscription renewed with **Invoice** whose next invoice date has been reached:

- A **customer invoice** for customer subscriptions, or a **vendor bill** for vendor subscriptions.
- One document per period, dated on the first day of the period, with the subscription lines and prices and the period dates in the line labels.
- Missed periods are caught up, and no period starting after the subscription end date is invoiced.
- Each plan decides whether its renewal invoices are posted automatically or left as drafts (**Post Renewal Invoices**, disabled by default).

**No double renewal.** Every subscription has a **Renewal Document** (core module), and each renewal scheduled action only processes its own document. Invoices are the default only when no other integration applies: with *Subscription Sale* installed, customer subscriptions default to sale orders; with *Subscription Purchase* installed, vendor subscriptions default to purchase orders. The document can be changed on each subscription.

Smart buttons link the subscriptions and their invoices in both directions.
