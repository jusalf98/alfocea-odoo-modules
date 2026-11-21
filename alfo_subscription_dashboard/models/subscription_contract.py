from odoo import api, fields, models

# Months in one period of each periodicity (for an interval of 1).
MONTHS_PER_PERIOD = {
    "daily": 12 / 365,
    "weekly": 12 / 52,
    "monthly": 1,
    "yearly": 12,
}


class SubscriptionContract(models.Model):
    _inherit = "subscription.contract"

    recurring_monthly = fields.Monetary(
        string="MRR",
        compute="_compute_recurring_amounts",
        store=True,
        help="Monthly Recurring Revenue (or cost, for vendor subscriptions): the "
        "total per period of the subscription, normalized to one month.",
    )
    recurring_yearly = fields.Monetary(
        string="ARR",
        compute="_compute_recurring_amounts",
        store=True,
        help="Annual Recurring Revenue (or cost): MRR x 12.",
    )

    @api.depends("amount_total", "plan_id.periodicity", "plan_id.interval")
    def _compute_recurring_amounts(self):
        for contract in self:
            plan = contract.plan_id
            months = MONTHS_PER_PERIOD.get(plan.periodicity, 0) * (plan.interval or 0)
            monthly = contract.amount_total / months if months else 0.0
            contract.recurring_monthly = contract.currency_id.round(monthly)
            contract.recurring_yearly = contract.currency_id.round(monthly * 12)
