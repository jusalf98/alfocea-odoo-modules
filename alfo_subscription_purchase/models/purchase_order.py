from odoo import Command, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    subscription_contract_ids = fields.Many2many(
        "subscription.contract",
        relation="subscription_contract_purchase_order_rel",
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

    def button_confirm(self):
        # The Confirm buttons of the form ask for a preview: if the order changes
        # existing subscriptions, show them before confirming. Never in automatic
        # confirmations: they expect the order to be confirmed.
        context = self.env.context
        if (
            len(self) == 1
            and context.get("subscription_preview")
            and not context.get("subscription_skip_preview")
        ):
            preview_action = self._get_subscription_preview_action()
            if preview_action:
                return preview_action
        return super().button_confirm()

    def _confirm_after_subscription_preview(self):
        """Called by the preview wizard (``subscription.order.confirm``)."""
        return self.button_confirm()

    def _get_subscription_preview_action(self):
        """Preview wizard action, or None if no existing subscription changes."""
        self.ensure_one()
        requests = self._get_subscription_requests()
        rows = requests and self.env["subscription.contract"]._preview_from_orders(
            "purchase", requests
        )
        if not rows:
            return None
        return self.env["subscription.order.confirm"]._open_for(self, rows)

    def button_approve(self, force=False):
        # Every confirmed order goes through here, with or without double validation.
        res = super().button_approve(force=force)
        # Renewal orders come from a contract: they must not create another one.
        if not self.env.context.get("subscription_renewal"):
            self.filtered(
                lambda order: order.state in ("purchase", "done")
            )._create_subscription_contracts()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        # Undo what the cancelled orders changed in the subscriptions.
        contracts_by_order = self.env["subscription.contract"]._revert_order_changes(
            self.filtered(lambda order: order.state == "cancel")
        )
        for order, contracts in contracts_by_order.items():
            contracts.purchase_order_ids = [Command.unlink(order.id)]
        return res

    def action_view_subscription_contracts(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "alfo_subscription_core.subscription_contract_purchase_action"
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
        """Create or update the vendor subscriptions of the confirmed orders.

        Only the lines whose product has a vendor subscription plan are used. See
        ``subscription.contract._create_or_update_from_orders`` for the rules
        (add the quantity, add a line or create a new subscription). Runs as
        superuser: buyers don't need any subscription access right.
        """
        requests = self._get_subscription_requests()
        if not requests:
            return
        contracts_by_order = self.env[
            "subscription.contract"
        ]._create_or_update_from_orders(
            "purchase",
            requests,
            # "Confirm without adding" of the confirmation wizard
            only_new=self.env.context.get("subscription_only_new", False),
        )
        for order, contracts in contracts_by_order.items():
            contracts.purchase_order_ids = [Command.link(order.id)]

    def _get_subscription_requests(self):
        """Vendor subscription lines of the orders, by order and plan (see
        ``subscription.contract._create_or_update_from_orders``)."""
        lines_by_order_plan = (
            self.sudo()
            .order_line.filtered(
                lambda line: not line.display_type and line.product_id.purchase_plan_id
            )
            .grouped(lambda line: (line.order_id, line.product_id.purchase_plan_id))
        )
        return [
            {
                "order": order,
                "plan": plan,
                "partner": order.partner_id,
                "user": order.user_id,
                "company": order.company_id,
                "line_vals": [
                    line._prepare_subscription_contract_line_vals() for line in lines
                ],
            }
            for (order, plan), lines in lines_by_order_plan.items()
        ]
