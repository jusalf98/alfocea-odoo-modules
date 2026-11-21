from datetime import timedelta

from odoo import fields

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionReminders(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)
        cls.partner.email = "customer@example.com"
        cls.renewal_template = cls.env.ref(
            "alfo_subscription_core.mail_template_subscription_renewal_reminder"
        )
        cls.trial_template = cls.env.ref(
            "alfo_subscription_core.mail_template_subscription_trial_reminder"
        )
        cls.expiry_template = cls.env.ref(
            "alfo_subscription_core.mail_template_subscription_expiry_reminder"
        )

    def _send(self):
        return self.SubscriptionContract._cron_send_reminders()

    def test_renewal_reminder_sent_once(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.action_start()
        contract.next_invoice_date = self.today + timedelta(days=5)
        self.assertEqual(self._send().get(contract), self.renewal_template)
        self.assertIn("will be renewed soon", contract.message_ids[0].subject)
        self.assertIn(self.partner, contract.message_ids[0].partner_ids)
        # Not again for the same renewal.
        self.assertFalse(self._send().get(contract))

    def test_no_reminder_too_early_or_disabled(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.action_start()
        contract.next_invoice_date = self.today + timedelta(days=30)
        self.assertFalse(self._send().get(contract))
        contract.next_invoice_date = self.today + timedelta(days=2)
        self.plan_monthly.reminder_days = 0
        self.assertFalse(self._send().get(contract))

    def test_trial_reminder(self):
        self.plan_trial.trial_days = 3
        contract = self._create_contract(self.plan_trial, self.today)
        contract.action_start()
        self.assertEqual(self._send().get(contract), self.trial_template)
        self.assertTrue(contract.trial_reminder_sent)
        self.assertFalse(self._send().get(contract))

    def test_expiry_reminder(self):
        contract = self._create_contract(
            self.plan_monthly, self.today, date_end=self.today + timedelta(days=4)
        )
        contract.action_start()
        contract.next_invoice_date = self.today + timedelta(days=60)
        self.assertEqual(self._send().get(contract), self.expiry_template)
        self.assertFalse(self._send().get(contract))

    def test_no_expiry_reminder_when_renewed_automatically(self):
        self.plan_monthly.auto_renew = True
        contract = self._create_contract(
            self.plan_monthly, self.today, date_end=self.today + timedelta(days=4)
        )
        contract.action_start()
        contract.next_invoice_date = self.today + timedelta(days=60)
        self.assertFalse(self._send().get(contract))

    def test_no_reminders_for_vendor_subscriptions(self):
        contract = self._create_contract(
            self.plan_monthly, self.today, contract_type="purchase"
        )
        contract.action_start()
        contract.next_invoice_date = self.today + timedelta(days=5)
        self.assertFalse(self._send().get(contract))
