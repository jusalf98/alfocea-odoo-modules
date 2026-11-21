from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

PERIODICITY_UNITS = {
    "daily": "days",
    "weekly": "weeks",
    "monthly": "months",
    "yearly": "years",
}
# Plan report: subscriptions listed (not finished) and those adding to the totals.
REPORT_OPEN_STATES = ("draft", "trial", "active", "paused")
REPORT_RUNNING_STATES = ("trial", "active")


class SubscriptionPlan(models.Model):
    _name = "subscription.plan"
    _description = "Subscription Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one("res.company", index=True, tracking=True)
    periodicity = fields.Selection(
        selection=[
            ("daily", "Day(s)"),
            ("weekly", "Week(s)"),
            ("monthly", "Month(s)"),
            ("yearly", "Year(s)"),
        ],
        required=True,
        default="monthly",
        tracking=True,
    )
    interval = fields.Integer(
        string="Repeat Every", required=True, default=1, tracking=True
    )
    trial_days = fields.Integer(
        help="Number of free days before the first invoice of the subscription.",
        tracking=True,
    )
    group_by_partner = fields.Boolean(
        string="One Subscription per Partner",
        tracking=True,
        help="When an order sells (or buys) a product of this plan that the partner "
        "does not have yet, add it as a new line to the open subscription of the "
        "partner with this plan. If unchecked, a new subscription is created.",
    )
    reminder_days = fields.Integer(
        default=7,
        tracking=True,
        help="Days before a renewal, the end of the trial or the end of the "
        "subscription to send a reminder email to the customer. 0 disables them.",
    )
    auto_renew = fields.Boolean(
        string="Renew Automatically",
        tracking=True,
        help="When a subscription with an end date reaches it, extend it one more "
        "period instead of expiring it, unless the customer asked not to renew "
        "it before the notice period.",
    )
    notice_days = fields.Integer(
        default=30,
        tracking=True,
        help="Days before the end date until which the customer can ask not to "
        "renew an automatically renewed subscription.",
    )
    description = fields.Text(translate=True)
    contract_ids = fields.One2many(
        "subscription.contract", "plan_id", string="Contracts"
    )
    contract_count = fields.Integer(compute="_compute_contract_count")
    billing_label = fields.Char(string="Billing", compute="_compute_billing_label")
    trial_label = fields.Char(string="Free Trial", compute="_compute_billing_label")

    @api.depends("periodicity", "interval", "trial_days")
    @api.depends_context("lang")
    def _compute_billing_label(self):
        for plan in self:
            plan.billing_label = plan._get_billing_label()
            plan.trial_label = plan._get_trial_label()

    def _get_billing_label(self):
        """Billing periodicity in natural language: "every month", "every 3 weeks"."""
        self.ensure_one()
        if not self.periodicity or not self.interval:
            return ""
        _ = self.env._
        if self.interval == 1:
            return {
                "daily": _("every day"),
                "weekly": _("every week"),
                "monthly": _("every month"),
                "yearly": _("every year"),
            }[self.periodicity]
        return {
            "daily": _("every %(count)s days", count=self.interval),
            "weekly": _("every %(count)s weeks", count=self.interval),
            "monthly": _("every %(count)s months", count=self.interval),
            "yearly": _("every %(count)s years", count=self.interval),
        }[self.periodicity]

    def _get_trial_label(self):
        """Trial length in natural language: "1 day", "14 days", "" (no trial)."""
        self.ensure_one()
        if not self.trial_days:
            return ""
        if self.trial_days == 1:
            return self.env._("1 day")
        return self.env._("%(count)s days", count=self.trial_days)

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

    @api.constrains("reminder_days", "notice_days")
    def _check_reminder_and_notice_days(self):
        if self.filtered(lambda plan: plan.reminder_days < 0 or plan.notice_days < 0):
            raise ValidationError(
                self.env._("The reminder and notice days cannot be negative.")
            )

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

    # ------------------------------------------------------------------
    # Plan report
    # ------------------------------------------------------------------

    def _get_report_contracts(self):
        """Open subscriptions of the plan, for the plan report."""
        self.ensure_one()
        return self.contract_ids.filtered(
            lambda contract: contract.state in REPORT_OPEN_STATES
        ).sorted(
            lambda contract: (
                contract.contract_type != "sale",  # customers first
                contract.partner_id.display_name or "",
                contract.name,
            )
        )

    def _get_report_totals(self):
        """Total per period of the running subscriptions (trial and active), by
        contract type and currency: plans can be shared by several companies."""
        self.ensure_one()
        totals = defaultdict(float)
        for contract in self.contract_ids.filtered(
            lambda contract: contract.state in REPORT_RUNNING_STATES
        ):
            totals[(contract.contract_type, contract.currency_id)] += (
                contract.amount_total
            )
        return [
            {"contract_type": contract_type, "currency": currency, "amount": amount}
            for (contract_type, currency), amount in sorted(
                # customers first, then by currency
                totals.items(),
                key=lambda item: (item[0][0] != "sale", item[0][1].name),
            )
        ]
