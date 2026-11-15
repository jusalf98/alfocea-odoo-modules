from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

SEQUENCE_CODES = {
    "sale": "subscription.contract",
    "purchase": "subscription.contract.purchase",
}


class SubscriptionContract(models.Model):
    _name = "subscription.contract"
    _description = "Subscription Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        index="trigram",
    )
    contract_type = fields.Selection(
        selection=[("sale", "Sale"), ("purchase", "Purchase")],
        required=True,
        default="sale",
        tracking=True,
        index=True,
    )
    # Customer or vendor depending on the contract type: the label is set in the views.
    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        tracking=True,
        check_company=True,
        index=True,
    )
    plan_id = fields.Many2one(
        "subscription.plan",
        required=True,
        tracking=True,
        check_company=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    date_start = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    date_end = fields.Date(string="End Date", tracking=True, copy=False)
    trial_end_date = fields.Date(compute="_compute_trial_end_date", store=True)
    next_invoice_date = fields.Date(tracking=True, copy=False)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("trial", "Trial"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("cancelled", "Cancelled"),
            ("expired", "Expired"),
        ],
        required=True,
        default="draft",
        copy=False,
        tracking=True,
        index=True,
        group_expand="_expand_states",
    )
    line_ids = fields.One2many(
        "subscription.contract.line", "contract_id", string="Lines", copy=True
    )
    amount_total = fields.Monetary(
        string="Total", compute="_compute_amount_total", store=True
    )
    note = fields.Html()

    # The trial days are copied from the plan when the contract changes plan or
    # start date only: editing a plan must not alter contracts already running.
    @api.depends("date_start", "plan_id")
    def _compute_trial_end_date(self):
        for contract in self:
            trial_days = contract.plan_id.trial_days
            contract.trial_end_date = (
                contract.date_start + relativedelta(days=trial_days)
                if contract.date_start and trial_days
                else False
            )

    @api.depends("line_ids.price_subtotal")
    def _compute_amount_total(self):
        for contract in self:
            contract.amount_total = sum(contract.line_ids.mapped("price_subtotal"))

    def _expand_states(self, states, domain):
        return [key for key, _label in self._fields["state"].selection]

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for contract in self:
            if contract.date_end and contract.date_end < contract.date_start:
                raise ValidationError(
                    self.env._(
                        "The end date of %s cannot be earlier than its start date.",
                        contract.display_name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        IrSequence = self.env["ir.sequence"]
        default_type = self.default_get(["contract_type"]).get("contract_type", "sale")
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                contract_type = vals.get("contract_type") or default_type
                vals["name"] = (
                    IrSequence.next_by_code(SEQUENCE_CODES[contract_type]) or "/"
                )
        return super().create(vals_list)

    def action_start(self):
        self._check_states({"draft"})
        contracts_without_lines = self.filtered(lambda contract: not contract.line_ids)
        if contracts_without_lines:
            raise UserError(
                self.env._(
                    "Add at least one line before starting: %s",
                    ", ".join(contracts_without_lines.mapped("display_name")),
                )
            )
        for contract in self:
            contract.write(
                {
                    "state": contract._get_running_state(),
                    "next_invoice_date": contract._get_first_invoice_date(),
                }
            )

    def action_pause(self):
        self._check_states({"trial", "active"})
        self.write({"state": "paused"})

    def action_resume(self):
        self._check_states({"paused"})
        for contract in self:
            contract.state = contract._get_running_state()

    def action_cancel(self):
        self._check_states({"draft", "trial", "active", "paused"})
        self.write({"state": "cancelled"})

    def action_set_draft(self):
        self._check_states({"cancelled"})
        self.write({"state": "draft", "next_invoice_date": False})

    def _check_states(self, allowed_states):
        invalid_contracts = self.filtered(
            lambda contract: contract.state not in allowed_states
        )
        if invalid_contracts:
            raise UserError(
                self.env._(
                    "This action is not allowed for the subscriptions: %s",
                    ", ".join(invalid_contracts.mapped("display_name")),
                )
            )

    def _is_in_trial(self, today=None):
        self.ensure_one()
        today = today or fields.Date.context_today(self)
        return bool(self.trial_end_date and self.trial_end_date > today)

    def _get_running_state(self):
        self.ensure_one()
        return "trial" if self._is_in_trial() else "active"

    def _get_first_invoice_date(self):
        """First invoice at the end of the trial, otherwise at the start date."""
        self.ensure_one()
        return self.trial_end_date if self._is_in_trial() else self.date_start

    @api.model
    def _cron_update_states(self):
        """Move finished trials to active and finished contracts to expired."""
        today = fields.Date.context_today(self)
        self.search([("state", "=", "trial"), ("trial_end_date", "<=", today)]).write(
            {"state": "active"}
        )
        self.search(
            [
                ("state", "in", ("trial", "active", "paused")),
                ("date_end", "!=", False),
                ("date_end", "<", today),
            ]
        ).write({"state": "expired"})
