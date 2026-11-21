from odoo import api, fields, models

from odoo.addons.alfo_subscription_core.models.subscription_contract import (
    OPEN_STATES,
)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # The line starts a new subscription whose plan has a free trial: the
    # customer pays nothing now, the first invoice comes at the end of the trial.
    # Stored and only depending on the product and the customer, so it does not
    # change once the order is confirmed and the subscription exists.
    subscription_trial = fields.Boolean(
        string="Free Trial",
        compute="_compute_subscription_trial",
        store=True,
        precompute=True,
    )

    @api.depends("product_id", "order_id.partner_id")
    def _compute_subscription_trial(self):
        # Only quotations get a free trial: lines of confirmed orders (e.g. when
        # the module is installed on a database with orders) are never flagged,
        # so their discount can never be changed afterwards.
        candidates = self.filtered(
            lambda line: not line.display_type
            and line.order_id.state in ("draft", "sent")
            and line.order_id.partner_id
            and line.product_id.sudo().default_plan_id.trial_days
        )
        (self - candidates).subscription_trial = False
        if not candidates:
            return
        open_contracts = (
            self.env["subscription.contract"]
            .sudo()
            .search(
                [
                    ("contract_type", "=", "sale"),
                    ("partner_id", "in", candidates.order_id.partner_id.ids),
                    (
                        "plan_id",
                        "in",
                        candidates.product_id.sudo().default_plan_id.ids,
                    ),
                    ("state", "in", OPEN_STATES),
                ]
            )
        )
        partner_plans = {(c.partner_id.id, c.plan_id.id) for c in open_contracts}
        partner_plan_products = {
            (c.partner_id.id, c.plan_id.id, product.id)
            for c in open_contracts
            for product in c.line_ids.product_id
        }
        for line in candidates:
            plan = line.product_id.sudo().default_plan_id
            key = (line.order_id.partner_id.id, plan.id)
            # No trial when the product is bought again, or when it is added to
            # an existing subscription of the customer (plan grouped by partner).
            line.subscription_trial = key + (
                line.product_id.id,
            ) not in partner_plan_products and not (
                plan.group_by_partner and key in partner_plans
            )

    @api.depends("subscription_trial")
    def _compute_discount(self):
        res = super()._compute_discount()
        self.filtered("subscription_trial").discount = 100.0
        return res

    @api.depends("subscription_trial")
    def _compute_name(self):
        return super()._compute_name()

    def _get_sale_order_line_multiline_description_sale(self):
        description = super()._get_sale_order_line_multiline_description_sale()
        if self.subscription_trial:
            description += "\n" + self._get_subscription_trial_note()
        return description

    def _get_subscription_trial_note(self):
        """Text added to the line description, in the language of the context."""
        self.ensure_one()
        plan = self.product_id.sudo().default_plan_id
        return self.env._(
            "Free trial: %(trial)s. Then billed %(billing)s.",
            trial=plan._get_trial_label(),
            billing=plan._get_billing_label(),
        )

    def _prepare_subscription_contract_line_vals(self):
        """Contract line from the order line: discounted price, company currency.

        A free trial line has a 100% discount on the order only: the subscription
        gets its real price, and the trial note is removed from its description.
        """
        self.ensure_one()
        order = self.order_id
        discount = 0.0 if self.subscription_trial else (self.discount or 0.0)
        price_unit = self.price_unit * (1 - discount / 100.0)
        company_currency = order.company_id.currency_id
        if order.currency_id != company_currency:
            price_unit = order.currency_id._convert(
                price_unit,
                company_currency,
                order.company_id,
                order.date_order or order.create_date,
            )
        name = self.name
        if self.subscription_trial:
            note = self.with_context(
                lang=order._get_lang()
            )._get_subscription_trial_note()
            name = name.replace("\n" + note, "")
        return {
            "product_id": self.product_id.id,
            "name": name,
            "quantity": self.product_uom_qty,
            "price_unit": price_unit,
            # Free trial lines (100% discount) are not paid by the order.
            "paid": not (self.subscription_trial and self.discount >= 100.0),
        }
