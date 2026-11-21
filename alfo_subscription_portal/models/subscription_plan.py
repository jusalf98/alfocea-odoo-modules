from odoo import fields, models


class SubscriptionPlan(models.Model):
    _inherit = "subscription.plan"

    portal_allow_pause = fields.Boolean(
        string="Customers Can Pause",
        tracking=True,
        help="The customers can pause (and resume) their subscriptions with this "
        "plan from their portal.",
    )
    portal_allow_cancel = fields.Boolean(
        string="Customers Can Cancel",
        tracking=True,
        help="The customers can cancel their subscriptions with this plan from "
        "their portal. If the plan renews automatically, they can instead ask not "
        "to renew it (before the notice deadline).",
    )
