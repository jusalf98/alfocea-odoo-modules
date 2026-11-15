import logging

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)

# A contract still in trial whose next invoice date has been reached has finished
# its trial: the core cron that moves it to active may simply run later today.
RENEWABLE_STATES = ("trial", "active")


class SubscriptionContract(models.Model):
    _inherit = "subscription.contract"

    sale_order_ids = fields.Many2many(
        "sale.order",
        relation="subscription_contract_sale_order_rel",
        column1="contract_id",
        column2="order_id",
        string="Sale Orders",
        copy=False,
        readonly=True,
    )
    sale_order_count = fields.Integer(compute="_compute_sale_order_count")

    @api.depends("sale_order_ids")
    def _compute_sale_order_count(self):
        for contract in self:
            contract.sale_order_count = len(contract.sale_order_ids)

    def action_view_sale_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("sale.action_orders")
        orders = self.sale_order_ids
        if len(orders) == 1:
            action.update(
                {"views": [(False, "form")], "view_mode": "form", "res_id": orders.id}
            )
        else:
            action["domain"] = [("id", "in", orders.ids)]
        return action

    @api.model
    def _cron_create_recurring_sale_orders(self):
        """Create the sale orders of the customer subscriptions that are due."""
        today = fields.Date.context_today(self)
        for contract in self.search(self._get_renewal_domain(today)):
            # One savepoint per contract: an error in one subscription (archived
            # product, wrong configuration...) must not block the other renewals.
            try:
                with self.env.cr.savepoint():
                    contract._create_recurring_sale_orders(today)
            except Exception:
                _logger.exception(
                    "Subscription %s: the renewal sale order could not be created",
                    contract.display_name,
                )

    @api.model
    def _get_renewal_domain(self, date):
        return [
            ("contract_type", "=", "sale"),
            ("state", "in", RENEWABLE_STATES),
            ("next_invoice_date", "!=", False),
            ("next_invoice_date", "<=", date),
        ]

    def _create_recurring_sale_orders(self, date):
        """Create one sale order per due period up to ``date``.

        Missed periods (e.g. the server was down) are caught up, one order each.
        No period starting after the end date of the contract is ordered. The next
        invoice date is moved to the start of the first period not ordered yet.
        """
        self.ensure_one()
        vals_list = []
        period_start = self.next_invoice_date
        while period_start <= date and (
            not self.date_end or period_start <= self.date_end
        ):
            next_period_start = self.plan_id._get_next_date(period_start)
            vals_list.append(
                self._prepare_renewal_sale_order_vals(
                    period_start, next_period_start - relativedelta(days=1)
                )
            )
            period_start = next_period_start
        if not vals_list:
            return self.env["sale.order"]

        orders = self.env["sale.order"].create(vals_list)
        self.write(
            {
                "next_invoice_date": period_start,
                "sale_order_ids": [Command.link(order.id) for order in orders],
            }
        )
        if self.plan_id.sale_order_auto_confirm:
            orders.with_context(subscription_renewal=True).action_confirm()
        return orders

    def _prepare_renewal_sale_order_vals(self, period_start, period_end):
        self.ensure_one()
        company = self.company_id
        pricelist = self.partner_id.with_company(company).property_product_pricelist
        currency = pricelist.currency_id or company.currency_id
        vals = {
            "partner_id": self.partner_id.id,
            "company_id": company.id,
            "pricelist_id": pricelist.id,
            "origin": self.name,
            "order_line": [
                Command.create(
                    line._prepare_renewal_sale_order_line_vals(
                        period_start, period_end, currency
                    )
                )
                for line in self.line_ids
            ],
        }
        # Same salesperson and team as the order that created the subscription.
        origin_order = self.sale_order_ids.sorted("id")[:1]
        if origin_order:
            vals["user_id"] = origin_order.user_id.id
            vals["team_id"] = origin_order.team_id.id
        return vals
