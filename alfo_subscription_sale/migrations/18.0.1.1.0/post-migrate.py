from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """18.0.1.1.0: the core module adds the renewal document of the contracts.

    When the core module is updated, the new field is computed before this module
    is loaded, so the existing customer subscriptions get "Nothing" and would never
    be renewed. Renew them with sale orders, now that this module is loaded.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["subscription.contract"].search(
        [("contract_type", "=", "sale"), ("renewal_document", "=", "none")]
    )._reset_renewal_document()
