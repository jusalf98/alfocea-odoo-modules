from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    default_plan_id = fields.Many2one(
        "subscription.plan",
        string="Subscription Plan",
        check_company=True,
        groups="alfo_subscription_core.group_subscription_manager",
        help="When this product is sold, a subscription contract with this plan is "
        "created and started automatically for the customer.",
    )
