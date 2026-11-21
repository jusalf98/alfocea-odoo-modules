from odoo import fields, models


class SubscriptionContractOrderChange(models.Model):
    """What a confirmed order changed in a subscription, so that cancelling the
    order can revert exactly that (and nothing else)."""

    _name = "subscription.contract.order.change"
    _description = "Subscription Change from an Order"
    _order = "id desc"

    contract_id = fields.Many2one(
        "subscription.contract", required=True, ondelete="cascade", index=True
    )
    res_model = fields.Char(string="Order Model", required=True, index=True)
    res_id = fields.Many2oneReference(
        string="Order ID", model_field="res_model", required=True, index=True
    )
    order_name = fields.Char(string="Order")
    change_type = fields.Selection(
        selection=[
            ("quantity", "Quantity added"),
            ("new_line", "Line added"),
            ("new_subscription", "Subscription created"),
        ],
        required=True,
    )
    contract_line_id = fields.Many2one(
        "subscription.contract.line", ondelete="set null"
    )
    product_id = fields.Many2one("product.product")
    quantity = fields.Float(digits="Product Unit of Measure")
    reverted = fields.Boolean(readonly=True)
