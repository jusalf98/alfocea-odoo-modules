from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    purchase_plan_id = fields.Many2one(
        "subscription.plan",
        string="Vendor Subscription Plan",
        check_company=True,
        groups="alfo_subscription_core.group_subscription_manager",
        help="When this product is purchased, a vendor subscription with this plan "
        "is created and started automatically for the vendor.",
    )
