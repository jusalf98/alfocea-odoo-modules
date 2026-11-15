from odoo import fields, models


class SubscriptionPlan(models.Model):
    _inherit = "subscription.plan"

    sale_order_auto_confirm = fields.Boolean(
        string="Confirm Renewal Orders",
        default=True,
        help="Confirm automatically the sale orders generated on each renewal of "
        "the customer subscriptions with this plan. If unchecked, they are left "
        "as quotations to review.",
    )
