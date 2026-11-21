from odoo import Command, api, fields, models


class SubscriptionOrderConfirm(models.TransientModel):
    """Shown when confirming an order that changes existing subscriptions: lists
    what the subscriptions already have and what the order would add."""

    _name = "subscription.order.confirm"
    _description = "Confirm Order Subscription Changes"

    res_model = fields.Char(string="Order Model", required=True, readonly=True)
    res_id = fields.Many2oneReference(
        string="Order", model_field="res_model", required=True, readonly=True
    )
    order_name = fields.Char(readonly=True)
    line_ids = fields.One2many(
        "subscription.order.confirm.line", "wizard_id", string="Lines", readonly=True
    )

    @api.model
    def _open_for(self, order, rows):
        """Wizard action for ``order`` with the rows of
        ``subscription.contract._preview_from_orders``."""
        new_subscription = self.env._("New subscription")
        wizard = self.create(
            {
                "res_model": order._name,
                "res_id": order.id,
                "order_name": order.display_name,
                "line_ids": [
                    Command.create(
                        {
                            "contract_name": row["contract"].name or new_subscription,
                            "plan_name": row["plan"].name,
                            "product_id": row["product_id"],
                            "name": row["name"],
                            "current_quantity": row["current_quantity"],
                            "added_quantity": row["added_quantity"],
                            "change": row["change"],
                        }
                    )
                    for row in rows
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Subscription changes"),
            "res_model": self._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }

    def action_confirm(self):
        """Confirm the order, applying the subscription changes shown."""
        self.ensure_one()
        return (
            self._get_order()
            .with_context(subscription_skip_preview=True)
            ._confirm_after_subscription_preview()
        )

    def action_confirm_without_adding(self):
        """Confirm the order without changing the existing subscriptions.

        Those products are just sold (or bought) once. New subscriptions are
        still created, so a free trial line is invoiced at the end of its trial.
        """
        self.ensure_one()
        order = self._get_order()
        skipped = self.line_ids.filtered(
            lambda line: line.change in ("quantity", "new_line")
        )
        order.message_post(
            body=self.env._(
                "Confirmed without adding products to the existing subscriptions"
                " %(subscriptions)s.",
                subscriptions=", ".join(sorted(set(skipped.mapped("contract_name")))),
            )
        )
        return order.with_context(
            subscription_skip_preview=True, subscription_only_new=True
        )._confirm_after_subscription_preview()

    def _get_order(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id).exists()
