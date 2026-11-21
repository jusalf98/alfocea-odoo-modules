# Integration module that renews each contract type with orders.
ORDER_MODULES = {
    "sale": "alfo_subscription_sale",
    "purchase": "alfo_subscription_purchase",
}


def post_init_hook(env):
    """Subscriptions without renewal document: renew them with invoices, unless
    the orders module of their type is installed or being installed in the same
    run. Those are left to that module (orders are preferred), whatever the order
    in which the modules are loaded."""
    order_modules = set(
        env["ir.module.module"]
        .search(
            [
                ("name", "in", list(ORDER_MODULES.values())),
                ("state", "in", ("installed", "to install", "to upgrade")),
            ]
        )
        .mapped("name")
    )
    invoice_types = [
        contract_type
        for contract_type, module in ORDER_MODULES.items()
        if module not in order_modules
    ]
    env["subscription.contract"].search(
        [("contract_type", "in", invoice_types), ("renewal_document", "=", "none")]
    )._reset_renewal_document()
