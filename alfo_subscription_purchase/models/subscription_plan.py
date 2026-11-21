from odoo import fields, models


class SubscriptionPlan(models.Model):
    _inherit = "subscription.plan"

    purchase_order_auto_confirm = fields.Boolean(
        string="Confirm Renewal Purchase Orders",
        default=True,
        tracking=True,
        help="Confirm automatically the purchase orders generated on each renewal "
        "of the vendor subscriptions with this plan. If unchecked, they are left "
        "as requests for quotation to review.",
    )
