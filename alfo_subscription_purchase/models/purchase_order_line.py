from odoo import models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _prepare_subscription_contract_line_vals(self):
        """Contract line from the order line: discounted price, company currency."""
        self.ensure_one()
        order = self.order_id
        price_unit = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        company_currency = order.company_id.currency_id
        if order.currency_id != company_currency:
            price_unit = order.currency_id._convert(
                price_unit,
                company_currency,
                order.company_id,
                order.date_order or order.create_date,
            )
        return {
            "product_id": self.product_id.id,
            "name": self.name,
            "quantity": self.product_qty,
            "price_unit": price_unit,
        }
