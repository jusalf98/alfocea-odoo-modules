from odoo import models


class SubscriptionContractLine(models.Model):
    _inherit = "subscription.contract.line"

    def _prepare_renewal_purchase_order_line_vals(self, period, currency, date_planned):
        """Purchase order line of one period: contract price, period in the name."""
        self.ensure_one()
        return {
            "product_id": self.product_id.id,
            "name": f"{self.name}\n{period}",
            "product_qty": self.quantity,
            "price_unit": self._get_renewal_price_unit(currency),
            "date_planned": date_planned,
        }
