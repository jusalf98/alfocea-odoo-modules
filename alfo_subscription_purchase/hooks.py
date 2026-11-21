def post_init_hook(env):
    """Vendor subscriptions without renewal document: renew them with purchase
    orders. Only this module's contract type, so the result does not depend on the
    order in which the integration modules are loaded."""
    env["subscription.contract"].search(
        [("contract_type", "=", "purchase"), ("renewal_document", "=", "none")]
    )._reset_renewal_document()
