from odoo import fields
from odoo.tests import new_test_user
from odoo.tools import mute_logger

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionRenewalFailure(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)
        cls.responsible = new_test_user(
            cls.env,
            login="sub_responsible",
            groups="base.group_user,alfo_subscription_core.group_subscription_user",
        )

    @mute_logger("odoo.addons.alfo_subscription_core.models.subscription_contract")
    def test_failed_renewal_creates_one_activity(self):
        contract = self._create_contract(
            self.plan_monthly, self.today, user_id=self.responsible.id
        )
        contract.action_start()
        # A renewal method that fails (e.g. a broken configuration).
        for _attempt in range(2):
            self.SubscriptionContract._process_renewals("none", "_missing_method")
        activity = contract.activity_ids
        self.assertEqual(len(activity), 1)
        self.assertEqual(activity.user_id, self.responsible)
        self.assertEqual(activity.summary, "The renewal failed")
        self.assertIn(contract.name, activity.note)
