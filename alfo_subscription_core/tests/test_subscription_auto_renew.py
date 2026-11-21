from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionAutoRenew(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)
        cls.plan_monthly.write({"auto_renew": True, "notice_days": 10})

    def _contract_ending(self, days_from_today):
        contract = self._create_contract(
            self.plan_monthly,
            self.today - relativedelta(months=1),
            date_end=self.today + timedelta(days=days_from_today),
        )
        contract.action_start()
        return contract

    def test_end_date_is_renewed_instead_of_expired(self):
        contract = self._contract_ending(-1)
        old_end = contract.date_end
        self.SubscriptionContract._cron_update_states()
        self.assertEqual(contract.state, "active")
        self.assertEqual(contract.date_end, old_end + relativedelta(months=1))
        self.assertIn("Renewed automatically", contract.message_ids[0].body)

    def test_do_not_renew_expires_it(self):
        contract = self._contract_ending(20)
        self.assertEqual(
            contract.notice_deadline, contract.date_end - timedelta(days=10)
        )
        contract.action_do_not_renew()
        self.assertTrue(contract.do_not_renew)
        contract.date_end = self.today - timedelta(days=1)
        self.SubscriptionContract._cron_update_states()
        self.assertEqual(contract.state, "expired")
        self.assertEqual(contract.date_closed, contract.date_end)

    def test_do_not_renew_after_the_notice_deadline(self):
        contract = self._contract_ending(5)
        with self.assertRaises(UserError):
            contract.action_do_not_renew()

    def test_renew_again(self):
        contract = self._contract_ending(20)
        contract.action_do_not_renew()
        contract.action_renew_again()
        self.assertFalse(contract.do_not_renew)

    def test_without_auto_renew_it_expires(self):
        self.plan_monthly.auto_renew = False
        contract = self._contract_ending(-1)
        self.SubscriptionContract._cron_update_states()
        self.assertEqual(contract.state, "expired")
