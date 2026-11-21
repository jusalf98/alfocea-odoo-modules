import logging
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import format_date

_logger = logging.getLogger(__name__)

# A contract still in trial whose next invoice date has been reached has finished
# its trial: the cron that moves it to active may simply run later that day.
RENEWABLE_STATES = ("trial", "active")
# A partner already "has" a subscription while it is not finished.
OPEN_STATES = ("draft", "trial", "active", "paused")

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
    # Extended by the integration modules (sale order, purchase order, invoice).
    # Each renewal scheduled action only processes the contracts of its document,
    # so a subscription is never renewed twice.
    renewal_document = fields.Selection(
        selection=[("none", "Nothing")],
        required=True,
        compute="_compute_renewal_document",
        store=True,
        readonly=False,
        precompute=True,
        tracking=True,
        help="Document created automatically on each period of the subscription.",
    )
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
    order_change_ids = fields.One2many(
        "subscription.contract.order.change",
        "contract_id",
        string="Changes from Orders",
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
        help="Gets the activities of the subscription, e.g. when a renewal fails.",
    )
    # Churn analysis: why and when the subscription was closed (cancelled or
    # expired).
    close_reason_id = fields.Many2one(
        "subscription.close.reason", string="Close Reason", tracking=True, copy=False
    )
    date_closed = fields.Date(string="Closed On", readonly=True, copy=False)
    # Pause: renewals are shifted by the paused days when resumed.
    paused_date = fields.Date(string="Paused On", readonly=True, copy=False)
    resume_date = fields.Date(
        tracking=True,
        copy=False,
        help="The subscription is resumed automatically on this date.",
    )
    # Automatic renewal of the end date (plan "Renew Automatically").
    auto_renew = fields.Boolean(related="plan_id.auto_renew")
    do_not_renew = fields.Boolean(
        tracking=True,
        copy=False,
        help="The customer asked not to renew the subscription: it expires at its "
        "end date.",
    )
    notice_deadline = fields.Date(
        compute="_compute_notice_deadline",
        help="Last day to ask not to renew the subscription.",
    )
    # Reminder emails already sent (each one is sent once).
    renewal_reminder_date = fields.Date(copy=False, readonly=True)
    trial_reminder_sent = fields.Boolean(copy=False, readonly=True)
    expiry_reminder_sent = fields.Boolean(copy=False, readonly=True)

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

    @api.depends("date_end", "plan_id.notice_days")
    def _compute_notice_deadline(self):
        for contract in self:
            contract.notice_deadline = (
                contract.date_end - relativedelta(days=contract.plan_id.notice_days)
                if contract.date_end
                else False
            )

    @api.depends("contract_type")
    def _compute_renewal_document(self):
        for contract in self:
            contract.renewal_document = contract._get_default_renewal_document()

    def _get_default_renewal_document(self):
        """Hook: the integration modules return their document for this contract."""
        self.ensure_one()
        return "none"

    def _reset_renewal_document(self):
        """Set the default renewal document, with all installed modules loaded.

        Used by the install hooks and migration scripts of the integration modules:
        when a module is installed or updated, the renewal document of existing
        contracts may have been computed before the other integrations were loaded.
        """
        for document, contracts in self.grouped(
            lambda contract: contract._get_default_renewal_document()
        ).items():
            contracts.renewal_document = document

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

    def action_pause(self, resume_date=False):
        self._check_states({"trial", "active"})
        self.write(
            {
                "state": "paused",
                "paused_date": fields.Date.context_today(self),
                "resume_date": resume_date,
            }
        )

    def action_resume(self):
        """Resume the subscription. Its dates (next invoice, end of the trial if
        not finished, end date) move forward as many days as it was paused, so
        the customer does not pay for the paused time."""
        self._check_states({"paused"})
        today = fields.Date.context_today(self)
        for contract in self:
            vals = {"paused_date": False, "resume_date": False}
            paused_days = (
                (today - contract.paused_date).days if contract.paused_date else 0
            )
            if paused_days > 0:
                shift = relativedelta(days=paused_days)
                for field_name in ("next_invoice_date", "date_end"):
                    if contract[field_name]:
                        vals[field_name] = contract[field_name] + shift
                if (
                    contract.trial_end_date
                    and contract.trial_end_date > contract.paused_date
                ):
                    vals["trial_end_date"] = contract.trial_end_date + shift
            contract.write(vals)
            contract.state = contract._get_running_state()
            if paused_days > 0:
                contract.message_post(
                    body=self.env._(
                        "Resumed after %(days)s days paused: its dates moved forward "
                        "as many days.",
                        days=paused_days,
                    )
                )

    def action_cancel(self):
        self._check_states({"draft", "trial", "active", "paused"})
        self.write(
            {"state": "cancelled", "date_closed": fields.Date.context_today(self)}
        )

    def action_set_draft(self):
        self._check_states({"cancelled"})
        self.write(
            {
                "state": "draft",
                "next_invoice_date": False,
                "date_closed": False,
                "close_reason_id": False,
            }
        )

    def action_open_cancel_wizard(self):
        return self._open_close_wizard("cancel")

    def action_open_pause_wizard(self):
        return self._open_close_wizard("pause")

    def _open_close_wizard(self, close_action):
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Cancel Subscription")
            if close_action == "cancel"
            else self.env._("Pause Subscription"),
            "res_model": "subscription.close.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_contract_ids": self.ids,
                "default_close_action": close_action,
            },
        }

    def action_open_change_plan_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Change Plan"),
            "res_model": "subscription.change.plan.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_contract_id": self.id},
        }

    def action_do_not_renew(self):
        """The customer does not want the subscription to be renewed: it expires
        at its end date. Only before the notice deadline of the plan."""
        today = fields.Date.context_today(self)
        for contract in self:
            if not (contract.auto_renew and contract.date_end):
                raise UserError(
                    self.env._(
                        "%s is not renewed automatically.", contract.display_name
                    )
                )
            if today > contract.notice_deadline:
                raise UserError(
                    self.env._(
                        "The notice period of %(subscription)s ended on "
                        "%(deadline)s: it will be renewed on %(end)s.",
                        subscription=contract.display_name,
                        deadline=format_date(self.env, contract.notice_deadline),
                        end=format_date(self.env, contract.date_end),
                    )
                )
        self.write({"do_not_renew": True})

    def action_renew_again(self):
        self.write({"do_not_renew": False})

    def action_end_trial(self):
        """End the free trial today (subscription administrators only).

        The subscription becomes active and the next invoice date moves forward
        as much as the trial is shortened: with a free trial, the first invoice
        is due today. The chatter records who ended it and the planned end.
        """
        if not (
            self.env.su
            or self.env.user.has_group(
                "alfo_subscription_core.group_subscription_manager"
            )
        ):
            raise AccessError(
                self.env._("Only subscription administrators can end a free trial.")
            )
        self._check_states({"trial"})
        today = fields.Date.context_today(self)
        for contract in self:
            planned_end = contract.trial_end_date
            vals = {"state": "active", "trial_end_date": today}
            if contract.next_invoice_date and planned_end and planned_end > today:
                vals["next_invoice_date"] = contract._get_next_date_after_trial(
                    planned_end, today
                )
            contract.write(vals)
            contract.message_post(
                body=self.env._(
                    "Free trial ended early by %(user)s on %(today)s "
                    "(planned end: %(planned)s).",
                    user=self.env.user.name,
                    today=format_date(self.env, today),
                    planned=format_date(self.env, planned_end),
                )
            )

    def _get_next_date_after_trial(self, planned_end, new_end):
        """Next invoice date when the trial ends on ``new_end`` instead of
        ``planned_end``: the same number of periods after the new end (0 for a
        free trial, 1 when the order already paid the first period)."""
        self.ensure_one()
        periods, date = 0, planned_end
        while date < self.next_invoice_date and periods < 1000:
            date = self.plan_id._get_next_date(date)
            periods += 1
        if date != self.next_invoice_date:
            # Not a whole number of periods after the trial: keep the distance.
            return self.next_invoice_date - (planned_end - new_end)
        next_date = new_end
        for _period in range(periods):
            next_date = self.plan_id._get_next_date(next_date)
        return next_date

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

    # ------------------------------------------------------------------
    # Subscriptions from orders: shared by the sale and purchase modules
    # ------------------------------------------------------------------

    @api.model
    def _create_or_update_from_orders(self, contract_type, requests, only_new=False):
        """Create or update the subscriptions of confirmed orders.

        For every subscription product of an order, in this order of priority:

        1. The partner has an open subscription with that plan that already
           contains the product: its quantity is added to that line.
        2. The plan groups the products by partner and the partner has an open
           subscription with that plan: the product is added as a new line.
        3. Otherwise a new subscription is created (one per order and plan) and
           started. If the order paid it, the order covers the first paid period
           and the first renewal is due one period later; if it was a free
           trial, the first renewal is at the end of the trial.

        An order is only linked to the subscriptions that contain its products.
        Runs as superuser: salesmen and buyers don't need subscription rights.

        With ``only_new``, cases 1 and 2 are skipped: the existing subscriptions
        are not changed (those products are just sold or bought once), and only
        the new subscriptions of case 3 are created. Used by "Confirm without
        adding" of the confirmation wizard: a free trial line still gets its
        subscription, so it is invoiced at the end of the trial.

        :param requests: list of dicts with the keys ``order``, ``plan``,
            ``partner``, ``company`` and ``line_vals`` (list of contract line
            values: product_id, name, quantity, price_unit, and optionally
            ``paid``, default True: the order charged that line).
        :return: dict {order: subscriptions created or updated for it}
        """
        Contract = self.sudo()
        contracts_by_key = self._get_open_contracts_by_key(contract_type, requests)
        today = fields.Date.context_today(self)
        result = defaultdict(Contract.browse)
        # Requests are processed one by one (and new subscriptions created one by
        # one): two orders confirmed together for the same partner and product
        # must add up in the same subscription.
        for req in requests:
            order, plan, partner = req["order"], req["plan"], req["partner"]
            key = (partner, plan)
            match = self._match_order_request(req, contracts_by_key[key])
            updated = Contract.browse()
            changes = []  # logged so that cancelling the order can revert them
            new_line_vals = match["new_line_vals"]
            # only_new: the existing subscriptions are left untouched.
            if not only_new:
                for line, vals in match["quantity_lines"]:
                    line.quantity += vals["quantity"]
                    updated |= line.contract_id
                    changes.append(("quantity", line, vals["quantity"]))
            if new_line_vals and match["target"]:
                if not only_new:
                    target = match["target"]
                    lines_before = target.line_ids
                    target.line_ids = [Command.create(vals) for vals in new_line_vals]
                    updated |= target
                    changes += [
                        ("new_line", line, line.quantity)
                        for line in target.line_ids - lines_before
                    ]
            elif new_line_vals:
                contract = Contract.create(
                    {
                        "contract_type": contract_type,
                        "partner_id": partner.id,
                        "plan_id": plan.id,
                        "company_id": req["company"].id,
                        "date_start": today,
                        "user_id": (req.get("user") or self.env.user).id,
                        "line_ids": [Command.create(vals) for vals in new_line_vals],
                    }
                )
                contract._start_from_order(order, paid=match["new_lines_paid"])
                contracts_by_key[key] |= contract
                result[order] |= contract
                changes += [
                    ("new_line", line, line.quantity) for line in contract.line_ids
                ]
                changes.append(("new_subscription", contract, 0.0))
            self._log_order_changes(order, changes)

            for contract in updated:
                contract.message_post_with_source(
                    "mail.message_origin_link",
                    render_values={"self": contract, "origin": order, "edit": True},
                    subtype_xmlid="mail.mt_note",
                )
            result[order] |= updated
        return dict(result)

    @api.model
    def _log_order_changes(self, order, changes):
        """Log what ``order`` changed: [(change_type, line or contract, qty)]."""
        if not changes:
            return
        vals_list = []
        for change_type, record, quantity in changes:
            is_contract = change_type == "new_subscription"
            contract = record if is_contract else record.contract_id
            vals_list.append(
                {
                    "contract_id": contract.id,
                    "res_model": order._name,
                    "res_id": order.id,
                    "order_name": order.display_name,
                    "change_type": change_type,
                    "contract_line_id": False if is_contract else record.id,
                    "product_id": False if is_contract else record.product_id.id,
                    "quantity": quantity,
                }
            )
        self.env["subscription.contract.order.change"].sudo().create(vals_list)

    @api.model
    def _revert_order_changes(self, orders):
        """Undo what the cancelled ``orders`` changed in the subscriptions.

        The quantities they added are subtracted (a line left at 0 is removed),
        and a subscription they created is cancelled when it has no line left.
        Renewal documents already created are not touched: only the next
        renewals change. Every change is reverted once, and the chatter of the
        subscription explains it.

        :return: dict {order: subscriptions changed}
        """
        Change = self.env["subscription.contract.order.change"].sudo()
        result = defaultdict(self.sudo().browse)
        for order in orders:
            changes = Change.search(
                [
                    ("res_model", "=", order._name),
                    ("res_id", "=", order.id),
                    ("reverted", "=", False),
                ],
                order="id",
            )
            if not changes:
                continue
            notes = defaultdict(list)
            for change in changes.filtered(lambda c: c.contract_line_id):
                line = change.contract_line_id
                notes[line.contract_id].append(
                    self.env._(
                        "%(product)s: -%(quantity)s",
                        product=line.product_id.display_name,
                        quantity=f"{change.quantity:g}",
                    )
                )
                if line.quantity - change.quantity > 0:
                    line.quantity -= change.quantity
                else:
                    line.unlink()
            for change in changes.filtered(
                lambda c: c.change_type == "new_subscription"
            ):
                contract = change.contract_id
                if not contract.line_ids and contract.state not in (
                    "cancelled",
                    "expired",
                ):
                    contract.action_cancel()
                    notes[contract].append(self.env._("subscription cancelled"))
            changes.write({"reverted": True})
            for contract, contract_notes in notes.items():
                contract.message_post(
                    body=self.env._(
                        "Order %(order)s was cancelled, its changes were reverted: "
                        "%(changes)s.",
                        order=order.display_name,
                        changes=", ".join(contract_notes),
                    )
                )
            result[order] |= changes.contract_id
        return dict(result)

    @api.model
    def _get_open_contracts_by_key(self, contract_type, requests):
        """Open subscriptions of the partners and plans of the requests, by
        (partner, plan), oldest first."""
        Contract = self.sudo()
        open_contracts = Contract.search(
            [
                ("contract_type", "=", contract_type),
                ("partner_id", "in", [req["partner"].id for req in requests]),
                ("plan_id", "in", [req["plan"].id for req in requests]),
                ("state", "in", OPEN_STATES),
            ],
            order="id",
        )
        contracts_by_key = defaultdict(Contract.browse)
        for contract in open_contracts:
            contracts_by_key[(contract.partner_id, contract.plan_id)] |= contract
        return contracts_by_key

    @api.model
    def _match_order_request(self, req, candidates):
        """Decide what happens to each line of an order request, without writing.

        Shared by the confirmation and its preview wizard, so both always apply
        the same rules (see ``_create_or_update_from_orders``).

        :param candidates: open subscriptions of the partner with the plan.
        :return: dict with
            ``quantity_lines``: [(existing contract line, vals)] whose quantity
            is increased; ``new_line_vals``: values of the lines that are not in
            any subscription yet; ``target``: existing subscription that gets
            those new lines (plan grouped by partner), or an empty recordset when
            a new subscription is created; ``new_lines_paid``: the order charged
            at least one of the new lines.
        """
        quantity_lines = []
        new_line_vals = []
        new_lines_paid = False
        for order_line_vals in req["line_vals"]:
            vals = dict(order_line_vals)
            paid = vals.pop("paid", True)
            line = candidates.line_ids.filtered(
                lambda contract_line, vals=vals: contract_line.product_id.id
                == vals["product_id"]
            )[:1]
            if line:
                quantity_lines.append((line, vals))
            else:
                new_line_vals.append(vals)
                new_lines_paid = new_lines_paid or paid
        target = candidates[:1] if req["plan"].group_by_partner else candidates[:0]
        return {
            "quantity_lines": quantity_lines,
            "new_line_vals": new_line_vals,
            "target": target,
            "new_lines_paid": new_lines_paid,
        }

    @api.model
    def _preview_from_orders(self, contract_type, requests):
        """What confirming the orders would do with the subscriptions.

        :return: list of dicts with the keys ``contract`` (existing subscription,
            or empty for a new one), ``plan``, ``product_id``, ``name``,
            ``current_quantity``, ``added_quantity`` and ``change`` (``current``:
            line already in the subscription and not changed, ``quantity``:
            quantity added to an existing line, ``new_line``: product added to an
            existing subscription, ``new_subscription``: line of a new
            subscription). Empty if no existing subscription would change.
        """
        contracts_by_key = self._get_open_contracts_by_key(contract_type, requests)
        rows = []
        new_subscription_rows = []
        for req in requests:
            plan = req["plan"]
            match = self._match_order_request(
                req, contracts_by_key[(req["partner"], plan)]
            )
            added_by_line = {line: vals for line, vals in match["quantity_lines"]}
            changed = match["target"] | match["target"].browse(
                [line.contract_id.id for line in added_by_line]
            )
            for contract in changed:
                for line in contract.line_ids:
                    added = added_by_line.get(line)
                    rows.append(
                        {
                            "contract": contract,
                            "plan": plan,
                            "product_id": line.product_id.id,
                            "name": line.name,
                            "current_quantity": line.quantity,
                            "added_quantity": added["quantity"] if added else 0.0,
                            "change": "quantity" if added else "current",
                        }
                    )
                if contract == match["target"]:
                    rows += [
                        {
                            "contract": contract,
                            "plan": plan,
                            "product_id": vals["product_id"],
                            "name": vals["name"],
                            "current_quantity": 0.0,
                            "added_quantity": vals["quantity"],
                            "change": "new_line",
                        }
                        for vals in match["new_line_vals"]
                    ]
            if match["new_line_vals"] and not match["target"]:
                new_subscription_rows += [
                    {
                        "contract": match["target"],
                        "plan": plan,
                        "product_id": vals["product_id"],
                        "name": vals["name"],
                        "current_quantity": 0.0,
                        "added_quantity": vals["quantity"],
                        "change": "new_subscription",
                    }
                    for vals in match["new_line_vals"]
                ]
        return rows + new_subscription_rows if rows else []

    def _start_from_order(self, order, paid=True):
        """Start a subscription just created from a confirmed order.

        :param paid: the order charges the subscription lines. Then it covers the
            first paid period (the one starting at the start date, or at the end
            of the trial), so the first renewal is due one period later. A free
            trial order (sale) charges nothing: the first renewal is the first
            invoice, at the end of the trial.
        """
        self.ensure_one()
        self.message_post_with_source(
            "mail.message_origin_link",
            render_values={"self": self, "origin": order},
            subtype_xmlid="mail.mt_note",
        )
        self.action_start()
        if paid:
            self.next_invoice_date = self.plan_id._get_next_date(self.next_invoice_date)

    # ------------------------------------------------------------------
    # Renewals: shared by the integration modules (sale, purchase, account)
    # ------------------------------------------------------------------

    @api.model
    def _get_renewal_domain(self, renewal_document, date):
        return [
            ("renewal_document", "=", renewal_document),
            ("state", "in", RENEWABLE_STATES),
            ("next_invoice_date", "!=", False),
            ("next_invoice_date", "<=", date),
        ]

    @api.model
    def _process_renewals(self, renewal_document, renew_method):
        """Call ``renew_method(date)`` on every contract due for this document.

        One savepoint per contract: an error in one subscription (archived
        product, wrong configuration...) is logged and does not block the others.
        """
        today = fields.Date.context_today(self)
        for contract in self.search(self._get_renewal_domain(renewal_document, today)):
            try:
                with self.env.cr.savepoint():
                    getattr(contract, renew_method)(today)
            except Exception as error:
                _logger.exception(
                    "Subscription %s: the renewal %s could not be created",
                    contract.display_name,
                    renewal_document,
                )
                contract._notify_renewal_failure(error)

    def _notify_renewal_failure(self, error):
        """To-do activity for the responsible of the subscription (once: while
        it is open, a new failure does not create another one)."""
        self.ensure_one()
        summary = self.env._("The renewal failed")
        todo = self.env.ref("mail.mail_activity_data_todo")
        if self.activity_ids.filtered(
            lambda activity: activity.activity_type_id == todo
            and activity.summary == summary
        ):
            return
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            summary=summary,
            note=self.env._(
                "The renewal of %(subscription)s could not be created: %(error)s",
                subscription=self.display_name,
                error=str(error),
            ),
            user_id=(self.user_id or self.env.ref("base.user_admin")).id,
        )

    def _get_due_periods(self, date):
        """Periods to renew up to ``date``, and the next invoice date after them.

        Missed periods (e.g. the server was down) are all returned, so they can
        be caught up. No period starting after the end date is returned.
        :return: ([(period_start, period_end), ...], next_invoice_date)
        """
        self.ensure_one()
        periods = []
        period_start = self.next_invoice_date
        while (
            period_start
            and period_start <= date
            and (not self.date_end or period_start <= self.date_end)
        ):
            next_period_start = self.plan_id._get_next_date(period_start)
            periods.append((period_start, next_period_start - relativedelta(days=1)))
            period_start = next_period_start
        return periods, period_start

    def _get_period_description(self, period_start, period_end):
        """Period text for the renewal documents, in the partner language."""
        self.ensure_one()
        env = self.with_context(lang=self.partner_id.lang or self.env.lang).env
        return env._(
            "Period: %(start)s - %(end)s",
            start=format_date(env, period_start),
            end=format_date(env, period_end),
        )

    @api.model
    def _cron_update_states(self):
        """Daily: resume the paused subscriptions whose resume date has come,
        move finished trials to active, renew automatically the end date of the
        subscriptions that must be renewed, and expire the finished ones."""
        today = fields.Date.context_today(self)
        to_resume = self.search(
            [
                ("state", "=", "paused"),
                ("resume_date", "!=", False),
                ("resume_date", "<=", today),
            ]
        )
        if to_resume:
            to_resume.action_resume()
        self.search([("state", "=", "trial"), ("trial_end_date", "<=", today)]).write(
            {"state": "active"}
        )
        finished = self.search(
            [
                ("state", "in", ("trial", "active", "paused")),
                ("date_end", "!=", False),
                ("date_end", "<", today),
            ]
        )
        to_renew = finished.filtered(
            lambda contract: contract.plan_id.auto_renew and not contract.do_not_renew
        )
        for contract in to_renew:
            contract._renew_end_date(today)
        for contract in finished - to_renew:
            contract.write({"state": "expired", "date_closed": contract.date_end})

    def _renew_end_date(self, today):
        """Extend the end date period by period until it is not past."""
        self.ensure_one()
        old_end = date_end = self.date_end
        while date_end < today:
            date_end = self.plan_id._get_next_date(date_end)
        self.write({"date_end": date_end, "expiry_reminder_sent": False})
        self.message_post(
            body=self.env._(
                "Renewed automatically: the end date moves from %(old)s to %(new)s.",
                old=format_date(self.env, old_end),
                new=format_date(self.env, date_end),
            )
        )

    # ------------------------------------------------------------------
    # Reminder emails to the customers
    # ------------------------------------------------------------------

    @api.model
    def _cron_send_reminders(self):
        """Daily: email the customers, ``plan.reminder_days`` before, about the
        next renewal, the end of the trial and the end of the subscription. Each
        reminder is sent once."""
        today = fields.Date.context_today(self)
        contracts = self.search(
            [
                ("contract_type", "=", "sale"),
                ("state", "in", ("trial", "active", "paused")),
                ("plan_id.reminder_days", ">", 0),
            ]
        )
        Template = self.env["mail.template"]
        renewal_template = self.env.ref(
            "alfo_subscription_core.mail_template_subscription_renewal_reminder"
        )
        trial_template = self.env.ref(
            "alfo_subscription_core.mail_template_subscription_trial_reminder"
        )
        expiry_template = self.env.ref(
            "alfo_subscription_core.mail_template_subscription_expiry_reminder"
        )
        sent = defaultdict(Template.browse)
        for contract in contracts:
            limit = today + relativedelta(days=contract.plan_id.reminder_days)
            if (
                contract.state == "trial"
                and not contract.trial_reminder_sent
                and contract.trial_end_date
                and today < contract.trial_end_date <= limit
            ):
                contract._send_reminder(trial_template)
                contract.trial_reminder_sent = True
                sent[contract] |= trial_template
            elif (
                contract.state == "active"
                and contract.next_invoice_date
                and today < contract.next_invoice_date <= limit
                and contract.renewal_reminder_date != contract.next_invoice_date
            ):
                contract._send_reminder(renewal_template)
                contract.renewal_reminder_date = contract.next_invoice_date
                sent[contract] |= renewal_template
            if (
                contract.date_end
                and not contract.expiry_reminder_sent
                and today <= contract.date_end <= limit
                and (not contract.auto_renew or contract.do_not_renew)
            ):
                contract._send_reminder(expiry_template)
                contract.expiry_reminder_sent = True
                sent[contract] |= expiry_template
        return dict(sent)

    def _send_reminder(self, template):
        """Email the template to the customer and keep it in the chatter."""
        self.ensure_one()
        self.message_post_with_source(
            template,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
