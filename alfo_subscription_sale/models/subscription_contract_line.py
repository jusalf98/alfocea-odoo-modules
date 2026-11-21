from odoo import models


class SubscriptionContractLine(models.Model):
    _inherit = "subscription.contract.line"

    def _prepare_renewal_sale_order_line_vals(self, period, currency):
        """Sale order line of one period: contract price, period in the description."""
        self.ensure_one()
        return {
            "product_id": self.product_id.id,
            "name": f"{self.name}\n{period}",
            "product_uom_qty": self.quantity,
            "price_unit": self._get_renewal_price_unit(currency),
        }
