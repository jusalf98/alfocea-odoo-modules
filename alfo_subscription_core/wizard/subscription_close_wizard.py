from odoo import fields, models


class SubscriptionCloseWizard(models.TransientModel):
    """Cancel or pause subscriptions, with a reason (churn analysis)."""

    _name = "subscription.close.wizard"
    _description = "Cancel or Pause Subscriptions"

    contract_ids = fields.Many2many("subscription.contract", string="Subscriptions")
    close_action = fields.Selection(
        selection=[("cancel", "Cancel"), ("pause", "Pause")],
        required=True,
        default="cancel",
    )
    reason_id = fields.Many2one("subscription.close.reason", string="Reason")
    note = fields.Text()
    resume_date = fields.Date(
        help="Optional: the subscription is resumed automatically on this date."
    )

    def action_apply(self):
        self.ensure_one()
        contracts = self.contract_ids
        if self.close_action == "cancel":
            contracts.action_cancel()
            contracts.close_reason_id = self.reason_id
        else:
            contracts.action_pause(resume_date=self.resume_date)
        if self.reason_id or self.note:
            body = self.env._(
                "%(action)s. Reason: %(reason)s. %(note)s",
                action=dict(
                    self._fields["close_action"]._description_selection(self.env)
                )[self.close_action],
                reason=self.reason_id.name or "-",
                note=self.note or "",
            )
            for contract in contracts:
                contract.message_post(body=body)
        return {"type": "ir.actions.act_window_close"}
