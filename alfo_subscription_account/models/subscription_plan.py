from odoo import fields, models


class SubscriptionPlan(models.Model):
    _inherit = "subscription.plan"

    invoice_auto_post = fields.Boolean(
        string="Post Renewal Invoices",
        tracking=True,
        help="Post automatically the invoices and vendor bills generated on each "
        "renewal of the subscriptions with this plan. If unchecked, they are left "
        "as drafts to review.",
    )
