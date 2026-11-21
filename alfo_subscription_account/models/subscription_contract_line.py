from odoo import models


class SubscriptionContractLine(models.Model):
    _inherit = "subscription.contract.line"

    def _prepare_renewal_invoice_line_vals(self, period):
        """Invoice line of one period: contract price, period in the label."""
        self.ensure_one()
        return {
            "product_id": self.product_id.id,
            "name": f"{self.name}\n{period}",
            "quantity": self.quantity,
            "price_unit": self.price_unit,
        }
