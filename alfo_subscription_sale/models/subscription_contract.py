from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class SubscriptionContract(models.Model):
    _inherit = "subscription.contract"

    renewal_document = fields.Selection(
        selection_add=[("sale_order", "Sale Order")],
        ondelete={"sale_order": lambda recs: recs.write({"renewal_document": "none"})},
    )
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

    @api.constrains("renewal_document", "contract_type")
    def _check_renewal_document_sale_order(self):
        if self.filtered(
            lambda c: c.renewal_document == "sale_order" and c.contract_type != "sale"
        ):
            raise ValidationError(
                self.env._(
                    "Only customer subscriptions can be renewed with sale orders."
                )
            )

    def _get_default_renewal_document(self):
        if self.contract_type == "sale":
            return "sale_order"
        return super()._get_default_renewal_document()

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
        self._process_renewals("sale_order", "_create_recurring_sale_orders")

    def _create_recurring_sale_orders(self, date):
        """Create one sale order per due period up to ``date``."""
        self.ensure_one()
        periods, next_invoice_date = self._get_due_periods(date)
        if not periods:
            return self.env["sale.order"]
        orders = self.env["sale.order"].create(
            [self._prepare_renewal_sale_order_vals(*period) for period in periods]
        )
        self.write(
            {
                "next_invoice_date": next_invoice_date,
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
        period = self._get_period_description(period_start, period_end)
        vals = {
            "partner_id": self.partner_id.id,
            "company_id": company.id,
            "pricelist_id": pricelist.id,
            "origin": self.name,
            "order_line": [
                Command.create(
                    line._prepare_renewal_sale_order_line_vals(period, currency)
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
