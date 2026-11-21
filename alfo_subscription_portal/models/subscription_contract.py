from odoo import fields, models


class SubscriptionContract(models.Model):
    _name = "subscription.contract"
    _inherit = ["subscription.contract", "portal.mixin"]

    def _compute_access_url(self):
        for contract in self:
            contract.access_url = f"/my/subscriptions/{contract.id}"

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.env._("Subscription - %s", self.name)

    def _portal_can_pause(self):
        self.ensure_one()
        return self.plan_id.portal_allow_pause and self.state in ("trial", "active")

    def _portal_can_resume(self):
        self.ensure_one()
        return self.plan_id.portal_allow_pause and self.state == "paused"

    def _portal_can_cancel(self):
        """Cancel now: plans that are not renewed automatically."""
        self.ensure_one()
        return (
            self.plan_id.portal_allow_cancel
            and not (self.auto_renew and self.date_end)
            and self.state in ("trial", "active", "paused")
        )

    def _portal_can_stop_renewal(self):
        """Ask not to renew: plans renewed automatically, before the deadline."""
        self.ensure_one()
        return (
            self.plan_id.portal_allow_cancel
            and self.auto_renew
            and self.date_end
            and not self.do_not_renew
            and self.state in ("trial", "active", "paused")
            and fields.Date.context_today(self) <= self.notice_deadline
        )
