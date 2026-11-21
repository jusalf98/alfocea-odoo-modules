1. As a subscription administrator, open a product and set its **Vendor Subscription Plan** (below the subscription plan, next to the product category).
2. Confirm a purchase order with that product. The vendor subscription (`PSUB/` reference) is created and started automatically. Use the **Subscriptions** smart button of the order to open it.
3. Every day, the scheduled action *Subscriptions: create renewal purchase orders* creates the purchase orders of the vendor subscriptions whose next invoice date is today or earlier. To test it without waiting, set the **Next Invoice Date** of an active vendor subscription to today and run the action from *Settings > Technical > Scheduled Actions*.
4. Use the **Purchase Orders** smart button of the subscription to see all its orders.
