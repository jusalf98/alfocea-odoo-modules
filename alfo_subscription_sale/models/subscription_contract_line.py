from odoo import fields, models
from odoo.tools import format_date


class SubscriptionContractLine(models.Model):
    _inherit = "subscription.contract.line"

    def _prepare_renewal_sale_order_line_vals(self, period_start, period_end, currency):
        """Sale order line of one period: contract price, period in the description."""
        self.ensure_one()
        contract = self.contract_id
        price_unit = self.price_unit
        if currency != self.currency_id:
            price_unit = self.currency_id._convert(
                price_unit, currency, contract.company_id, fields.Date.today()
            )
        # The description is read by the customer: use their language.
        env = self.with_context(lang=contract.partner_id.lang or self.env.lang).env
        period = env._(
            "Period: %(start)s - %(end)s",
            start=format_date(env, period_start),
            end=format_date(env, period_end),
        )
        return {
            "product_id": self.product_id.id,
            "name": f"{self.name}\n{period}",
            "product_uom_qty": self.quantity,
            "price_unit": price_unit,
        }
