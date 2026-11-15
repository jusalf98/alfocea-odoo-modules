from datetime import date

from odoo.exceptions import ValidationError

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionPlan(AlfoSubscriptionCoreCommon):
    def test_next_date_by_periodicity(self):
        start = date(2026, 1, 31)
        cases = [
            ("daily", 10, date(2026, 2, 10)),
            ("weekly", 2, date(2026, 2, 14)),
            ("monthly", 1, date(2026, 2, 28)),
            ("yearly", 2, date(2028, 1, 31)),
        ]
        for periodicity, interval, expected in cases:
            with self.subTest(periodicity=periodicity):
                self.plan_monthly.write(
                    {"periodicity": periodicity, "interval": interval}
                )
                self.assertEqual(self.plan_monthly._get_next_date(start), expected)

    def test_interval_must_be_positive(self):
        with self.assertRaises(ValidationError):
            self.plan_monthly.interval = 0

    def test_trial_days_cannot_be_negative(self):
        with self.assertRaises(ValidationError):
            self.plan_monthly.trial_days = -1

    def test_contract_count(self):
        self.assertEqual(self.plan_monthly.contract_count, 0)
        self._create_contract(self.plan_monthly, date(2026, 1, 1))
        self._create_contract(self.plan_monthly, date(2026, 2, 1))
        self.plan_monthly.invalidate_recordset(["contract_count"])
        self.assertEqual(self.plan_monthly.contract_count, 2)

    def test_action_view_contracts(self):
        action = self.plan_monthly.action_view_contracts()
        self.assertEqual(action["res_model"], "subscription.contract")
        self.assertEqual(action["domain"], [("plan_id", "=", self.plan_monthly.id)])
