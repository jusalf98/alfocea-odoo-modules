1. As a subscription administrator, open a product and set its **Subscription Plan** (next to the product category).
2. In the plan, choose whether the renewal orders are confirmed automatically (**Confirm Renewal Orders**, enabled by default).
3. Create a quotation with that product and confirm it. The subscription is created and started automatically. Use the **Subscriptions** smart button of the order to open it.
4. Every day, the scheduled action *Subscriptions: create renewal sale orders* creates the sale orders of the subscriptions whose next invoice date is today or earlier, and moves that date to the next period. To test it without waiting, set the **Next Invoice Date** of an active subscription to today and run the action from *Settings > Technical > Scheduled Actions*.
5. Use the **Sale Orders** smart button of the subscription to see all its orders.
