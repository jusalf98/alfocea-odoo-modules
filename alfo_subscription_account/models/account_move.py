from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    subscription_contract_id = fields.Many2one(
        "subscription.contract",
        string="Subscription",
        index="btree_not_null",
        copy=False,
        readonly=True,
        groups="alfo_subscription_core.group_subscription_user",
    )

    def action_view_subscription_contract(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "subscription.contract",
            "views": [(False, "form")],
            "res_id": self.subscription_contract_id.id,
        }
