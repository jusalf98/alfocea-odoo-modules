from odoo import fields
from odoo.tests import Form

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionClose(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)
        cls.reason = cls.env.ref("alfo_subscription_core.close_reason_too_expensive")

    def _running_contract(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.action_start()
        return contract

    def _wizard(self, contract, close_action):
        action = (
            contract.action_open_cancel_wizard()
            if close_action == "cancel"
            else contract.action_open_pause_wizard()
        )
        return Form(self.env[action["res_model"]].with_context(**action["context"]))

    def test_cancel_with_reason(self):
        contract = self._running_contract()
        wizard = self._wizard(contract, "cancel")
        wizard.reason_id = self.reason
        wizard.note = "Found a cheaper option"
        wizard.save().action_apply()
        self.assertEqual(contract.state, "cancelled")
        self.assertEqual(contract.close_reason_id, self.reason)
        self.assertEqual(contract.date_closed, self.today)
        self.assertIn("Found a cheaper option", contract.message_ids[0].body)

    def test_pause_with_resume_date(self):
        contract = self._running_contract()
        wizard = self._wizard(contract, "pause")
        wizard.resume_date = self.today
        wizard.save().action_apply()
        self.assertEqual(contract.state, "paused")
        self.assertEqual(contract.resume_date, self.today)
        self.assertFalse(contract.close_reason_id)

    def test_reset_to_draft_clears_the_close_data(self):
        contract = self._running_contract()
        contract.action_cancel()
        contract.close_reason_id = self.reason
        contract.action_set_draft()
        self.assertFalse(contract.date_closed)
        self.assertFalse(contract.close_reason_id)

    def test_change_plan(self):
        contract = self._create_contract(self.plan_trial, self.today)
        contract.action_start()
        trial_end, next_date = contract.trial_end_date, contract.next_invoice_date
        yearly = self._create_plan("Yearly", periodicity="yearly")
        action = contract.action_open_change_plan_wizard()
        wizard = Form(self.env[action["res_model"]].with_context(**action["context"]))
        wizard.plan_id = yearly
        wizard.save().action_apply()
        self.assertEqual(contract.plan_id, yearly)
        # The current period and the trial are kept.
        self.assertEqual(contract.trial_end_date, trial_end)
        self.assertEqual(contract.next_invoice_date, next_date)
        self.assertIn("every year", contract.message_ids[0].body)
