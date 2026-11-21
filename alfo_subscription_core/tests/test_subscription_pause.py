from datetime import timedelta
from unittest.mock import patch

from odoo import fields

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionPause(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)

    def _at(self, date):
        """Run as if today were ``date``."""
        return patch.object(fields.Date, "context_today", return_value=date)

    def test_resume_moves_the_dates_forward(self):
        contract = self._create_contract(
            self.plan_monthly, self.today, date_end=self.today + timedelta(days=100)
        )
        contract.action_start()
        next_date, end_date = contract.next_invoice_date, contract.date_end
        contract.action_pause()
        self.assertEqual(contract.paused_date, self.today)
        with self._at(self.today + timedelta(days=10)):
            contract.action_resume()
        self.assertEqual(contract.state, "active")
        self.assertEqual(contract.next_invoice_date, next_date + timedelta(days=10))
        self.assertEqual(contract.date_end, end_date + timedelta(days=10))
        self.assertFalse(contract.paused_date)
        self.assertIn("10 days paused", contract.message_ids[0].body)

    def test_trial_end_moves_when_paused_during_the_trial(self):
        contract = self._create_contract(self.plan_trial, self.today)
        contract.action_start()
        trial_end = contract.trial_end_date
        contract.action_pause()
        with self._at(self.today + timedelta(days=5)):
            contract.action_resume()
        self.assertEqual(contract.trial_end_date, trial_end + timedelta(days=5))
        self.assertEqual(contract.state, "trial")

    def test_cron_resumes_on_the_resume_date(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.action_start()
        contract.action_pause(resume_date=self.today + timedelta(days=3))
        self.SubscriptionContract._cron_update_states()
        self.assertEqual(contract.state, "paused")
        with self._at(self.today + timedelta(days=3)):
            self.SubscriptionContract._cron_update_states()
        self.assertEqual(contract.state, "active")
        self.assertEqual(contract.next_invoice_date, self.today + timedelta(days=3))
