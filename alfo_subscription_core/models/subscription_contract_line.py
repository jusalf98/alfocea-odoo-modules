from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SubscriptionContractLine(models.Model):
    _name = "subscription.contract.line"
    _description = "Subscription Contract Line"
    _order = "contract_id, sequence, id"
    _check_company_auto = True

    contract_id = fields.Many2one(
        "subscription.contract", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="contract_id.company_id", store=True)
    currency_id = fields.Many2one(related="contract_id.currency_id")
    contract_type = fields.Selection(related="contract_id.contract_type")
    product_id = fields.Many2one(
        "product.product",
        required=True,
        check_company=True,
        domain="[('purchase_ok', '=', True)] if contract_type == 'purchase' "
        "else [('sale_ok', '=', True)]",
    )
    name = fields.Text(
        string="Description",
        compute="_compute_name",
        store=True,
        readonly=False,
        precompute=True,
        required=True,
    )
    quantity = fields.Float(default=1.0, digits="Product Unit of Measure")
    price_unit = fields.Float(
        string="Unit Price",
        compute="_compute_price_unit",
        store=True,
        readonly=False,
        precompute=True,
        digits="Product Price",
    )
    price_subtotal = fields.Monetary(
        string="Subtotal", compute="_compute_price_subtotal", store=True
    )

    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.display_name

    @api.depends("product_id", "contract_type")
    def _compute_price_unit(self):
        for line in self:
            if line.contract_type == "purchase":
                line.price_unit = line._get_purchase_price_unit()
            else:
                line.price_unit = line.product_id.lst_price

    @api.depends("quantity", "price_unit")
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.constrains("quantity")
    def _check_quantity(self):
        if self.filtered(lambda line: line.quantity <= 0):
            raise ValidationError(self.env._("The quantity must be greater than 0."))

    def _get_renewal_price_unit(self, currency, date=None):
        """Contract price converted to the currency of the renewal document."""
        self.ensure_one()
        if not currency or currency == self.currency_id:
            return self.price_unit
        return self.currency_id._convert(
            self.price_unit,
            currency,
            self.company_id,
            date or fields.Date.context_today(self),
        )

    def _get_purchase_price_unit(self):
        """Vendor price of the product for the contract partner, else its cost."""
        self.ensure_one()
        contract = self.contract_id
        date = contract.date_start or fields.Date.context_today(self)
        seller = self.product_id._select_seller(
            partner_id=contract.partner_id,
            quantity=self.quantity or 1.0,
            date=date,
        )
        if not seller:
            return self.product_id.standard_price
        return seller.currency_id._convert(
            seller.price, self.currency_id, self.company_id, date
        )
