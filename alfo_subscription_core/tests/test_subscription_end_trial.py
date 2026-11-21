from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionEndTrial(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)
        cls.manager = new_test_user(
            cls.env,
            login="trial_manager",
            groups="base.group_user,alfo_subscription_core.group_subscription_manager",
        )
        cls.user = new_test_user(
            cls.env,
            login="trial_user",
            groups="base.group_user,alfo_subscription_core.group_subscription_user",
        )

    def _trial_contract(self):
        contract = self._create_contract(self.plan_trial, self.today)
        contract.action_start()
        self.assertEqual(contract.state, "trial")
        return contract

    def test_manager_ends_free_trial(self):
        contract = self._trial_contract()
        planned_end = contract.trial_end_date
        contract.with_user(self.manager).action_end_trial()
        self.assertEqual(contract.state, "active")
        self.assertEqual(contract.trial_end_date, self.today)
        # Free trial: the first invoice comes forward to today.
        self.assertEqual(contract.next_invoice_date, self.today)
        message = contract.message_ids[0]
        self.assertIn("Free trial ended early", message.body)
        self.assertIn(self.manager.name, message.body)
        self.assertIn(fields.Date.to_string(planned_end)[:4], message.body)

    def test_paid_first_period_moves_with_the_trial(self):
        contract = self._trial_contract()
        # The order already paid the first period after the trial.
        contract.next_invoice_date = contract.trial_end_date + relativedelta(months=1)
        contract.action_end_trial()
        self.assertEqual(
            contract.next_invoice_date, self.today + relativedelta(months=1)
        )

    def test_user_cannot_end_trial(self):
        contract = self._trial_contract()
        with self.assertRaises(AccessError):
            contract.with_user(self.user).action_end_trial()
        self.assertEqual(contract.state, "trial")

    def test_only_trial_subscriptions(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.action_start()
        with self.assertRaises(UserError):
            contract.action_end_trial()
