from odoo import Command, api, fields, models

# A customer already "has" a subscription for a plan while it is not finished.
OPEN_CONTRACT_STATES = ("draft", "trial", "active", "paused")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    subscription_contract_ids = fields.Many2many(
        "subscription.contract",
        relation="subscription_contract_sale_order_rel",
        column1="order_id",
        column2="contract_id",
        string="Subscriptions",
        copy=False,
        readonly=True,
        groups="alfo_subscription_core.group_subscription_user",
    )
    subscription_contract_count = fields.Integer(
        compute="_compute_subscription_contract_count",
        groups="alfo_subscription_core.group_subscription_user",
    )

    @api.depends("subscription_contract_ids")
    def _compute_subscription_contract_count(self):
        for order in self:
            order.subscription_contract_count = len(order.subscription_contract_ids)

    def action_confirm(self):
        res = super().action_confirm()
        # Renewal orders come from a contract: they must not create another one.
        if not self.env.context.get("subscription_renewal"):
            self._create_subscription_contracts()
        return res

    def action_view_subscription_contracts(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "alfo_subscription_core.subscription_contract_sale_action"
        )
        contracts = self.subscription_contract_ids
        if len(contracts) == 1:
            action.update(
                {
                    "views": [(False, "form")],
                    "view_mode": "form",
                    "res_id": contracts.id,
                }
            )
        else:
            action["domain"] = [("id", "in", contracts.ids)]
        return action

    def _create_subscription_contracts(self):
        """Create and start a subscription for each (customer, plan) of the orders.

        Only the lines whose product has a subscription plan are used. If the
        customer already has an open subscription with that plan, the order is
        linked to it instead of creating a new one. Runs as superuser: salesmen
        don't need any subscription access right to confirm the order.
        """
        orders = self.sudo()
        lines_by_order_plan = orders.order_line.filtered(
            lambda line: not line.display_type and line.product_id.default_plan_id
        ).grouped(lambda line: (line.order_id, line.product_id.default_plan_id))
        if not lines_by_order_plan:
            return

        Contract = self.env["subscription.contract"].sudo()
        open_contracts = Contract.search(
            [
                ("contract_type", "=", "sale"),
                ("partner_id", "in", orders.partner_id.ids),
                ("plan_id", "in", [plan.id for _order, plan in lines_by_order_plan]),
                ("state", "in", OPEN_CONTRACT_STATES),
            ],
            order="id",
        )
        contract_by_key = {}
        for contract in open_contracts:
            contract_by_key.setdefault(
                (contract.partner_id, contract.plan_id), contract
            )

        today = fields.Date.context_today(self)
        vals_by_key = {}
        orders_by_key = {}
        for (order, plan), lines in lines_by_order_plan.items():
            key = (order.partner_id, plan)
            existing = contract_by_key.get(key)
            if existing:
                existing.sale_order_ids = [Command.link(order.id)]
                continue
            orders_by_key.setdefault(key, order.browse())
            orders_by_key[key] |= order
            # Several orders of the same customer and plan in one batch: only the
            # first one defines the lines, the others are just linked.
            vals_by_key.setdefault(
                key, order._prepare_subscription_contract_vals(plan, lines, today)
            )

        if not vals_by_key:
            return
        keys = list(vals_by_key)
        contracts = Contract.create([vals_by_key[key] for key in keys])
        for key, contract in zip(keys, contracts, strict=True):
            contract.sale_order_ids = [Command.set(orders_by_key[key].ids)]
            contract.message_post_with_source(
                "mail.message_origin_link",
                render_values={"self": contract, "origin": orders_by_key[key][0]},
                subtype_xmlid="mail.mt_note",
            )
        contracts.action_start()
        # The confirmed order already covers the first period: the first renewal
        # order is due one period later (or at the end of the trial, if any).
        for contract in contracts.filtered(lambda c: c.state == "active"):
            contract.next_invoice_date = contract.plan_id._get_next_date(
                contract.next_invoice_date
            )

    def _prepare_subscription_contract_vals(self, plan, lines, date_start):
        self.ensure_one()
        return {
            "contract_type": "sale",
            "partner_id": self.partner_id.id,
            "plan_id": plan.id,
            "company_id": self.company_id.id,
            "date_start": date_start,
            "line_ids": [
                Command.create(line._prepare_subscription_contract_line_vals())
                for line in lines
            ],
        }
