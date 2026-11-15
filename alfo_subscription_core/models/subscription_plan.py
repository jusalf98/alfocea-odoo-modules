from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

PERIODICITY_UNITS = {
    "daily": "days",
    "weekly": "weeks",
    "monthly": "months",
    "yearly": "years",
}


class SubscriptionPlan(models.Model):
    _name = "subscription.plan"
    _description = "Subscription Plan"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", index=True)
    periodicity = fields.Selection(
        selection=[
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("yearly", "Year(s)"),
        ],
        required=True,
        default="monthly",
    )
    interval = fields.Integer(string="Repeat Every", required=True, default=1)
    trial_days = fields.Integer(
        help="Number of free days before the first invoice of the subscription."
    )
    description = fields.Text(translate=True)
    contract_ids = fields.One2many(
        "subscription.contract", "plan_id", string="Contracts"
    )
    contract_count = fields.Integer(compute="_compute_contract_count")

    @api.depends("contract_ids")
    def _compute_contract_count(self):
        counts = dict(
            self.env["subscription.contract"]._read_group(
                [("plan_id", "in", self.ids)], ["plan_id"], ["__count"]
            )
        )
        for plan in self:
            plan.contract_count = counts.get(plan, 0)

    @api.constrains("interval")
    def _check_interval(self):
        if self.filtered(lambda plan: plan.interval <= 0):
            raise ValidationError(self.env._("The interval must be greater than 0."))

    @api.constrains("trial_days")
    def _check_trial_days(self):
        if self.filtered(lambda plan: plan.trial_days < 0):
            raise ValidationError(self.env._("The trial days cannot be negative."))

    def action_view_contracts(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "alfo_subscription_core.subscription_contract_action"
        )
        action["domain"] = [("plan_id", "=", self.id)]
        action["context"] = {"default_plan_id": self.id}
        return action

    def _get_next_date(self, date):
        """Return the date one billing period after ``date``."""
        self.ensure_one()
        unit = PERIODICITY_UNITS[self.periodicity]
        return date + relativedelta(**{unit: self.interval})
