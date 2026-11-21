from odoo import api, fields, models
from odoo.exceptions import UserError


class SubscriptionChangePlanWizard(models.TransientModel):
    """Move a running subscription to another plan (e.g. monthly to yearly)."""

    _name = "subscription.change.plan.wizard"
    _description = "Change Subscription Plan"

    contract_id = fields.Many2one("subscription.contract", required=True)
    current_plan_id = fields.Many2one(related="contract_id.plan_id")
    company_id = fields.Many2one(related="contract_id.company_id")
    plan_id = fields.Many2one(
        "subscription.plan",
        string="New Plan",
        required=True,
        domain="[('id', '!=', current_plan_id), "
        "('company_id', 'in', [company_id, False])]",
    )
    note = fields.Text()

    @api.constrains("plan_id", "contract_id")
    def _check_plan(self):
        for wizard in self:
            if wizard.plan_id == wizard.contract_id.plan_id:
                raise UserError(
                    self.env._("Choose a plan different from the current one.")
                )

    def action_apply(self):
        """Change the plan. The current period, already invoiced, is kept: the
        next invoice date does not change and the following renewals use the
        new plan. The trial end date is kept too."""
        self.ensure_one()
        contract = self.contract_id
        if contract.state in ("cancelled", "expired"):
            raise UserError(
                self.env._("The plan of a closed subscription cannot be changed.")
            )
        old_plan = contract.plan_id
        trial_end_date = contract.trial_end_date
        contract.plan_id = self.plan_id
        # The trial end date is computed from the plan: restore it after the
        # change (writing both at once would recompute it afterwards).
        contract.trial_end_date = trial_end_date
        contract.message_post(
            body=self.env._(
                "Plan changed from %(old)s (%(old_billing)s) to %(new)s "
                "(%(new_billing)s). %(note)s",
                old=old_plan.name,
                old_billing=old_plan.billing_label,
                new=self.plan_id.name,
                new_billing=self.plan_id.billing_label,
                note=self.note or "",
            )
        )
        return {"type": "ir.actions.act_window_close"}
