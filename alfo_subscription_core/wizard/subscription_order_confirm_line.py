from odoo import api, fields, models


class SubscriptionOrderConfirmLine(models.TransientModel):
    _name = "subscription.order.confirm.line"
    _description = "Confirm Order Subscription Changes Line"

    wizard_id = fields.Many2one(
        "subscription.order.confirm", required=True, ondelete="cascade"
    )
    # Names, not links: salesmen and buyers may have no subscription access.
    contract_name = fields.Char(string="Subscription")
    plan_name = fields.Char(string="Plan")
    product_id = fields.Many2one("product.product")
    name = fields.Text(string="Description")
    current_quantity = fields.Float(
        string="In Subscription", digits="Product Unit of Measure"
    )
    added_quantity = fields.Float(string="Added", digits="Product Unit of Measure")
    total_quantity = fields.Float(
        string="Final Quantity",
        compute="_compute_total_quantity",
        digits="Product Unit of Measure",
    )
    change = fields.Selection(
        selection=[
            ("current", "Already in the subscription"),
            ("quantity", "Quantity added"),
            ("new_line", "Added to the subscription"),
            ("new_subscription", "New subscription"),
        ],
    )

    @api.depends("current_quantity", "added_quantity")
    def _compute_total_quantity(self):
        for line in self:
            line.total_quantity = line.current_quantity + line.added_quantity
