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

    def _flush_tracking(self):
        """Run the pending tracking, as a commit would (same as mail tests)."""
        self.env.flush_all()
        self.env.cr.flush()

    def test_changes_are_tracked_in_chatter(self):
        # BaseCommon disables tracking in its context: enable it for this test.
        plan = self.SubscriptionPlan.with_context(
            tracking_disable=False, mail_notrack=False
        ).create({"name": "Tracked", "periodicity": "monthly"})
        # Odoo does not track changes of records created in the same
        # transaction: flush the creation first, like a real save would.
        self._flush_tracking()
        plan.write({"interval": 3, "trial_days": 7})
        self._flush_tracking()
        tracking_values = self.env["mail.tracking.value"].search(
            [
                ("mail_message_id.model", "=", "subscription.plan"),
                ("mail_message_id.res_id", "=", plan.id),
            ]
        )
        self.assertEqual(
            set(tracking_values.field_id.mapped("name")), {"interval", "trial_days"}
        )

    def test_action_view_contracts(self):
        action = self.plan_monthly.action_view_contracts()
        self.assertEqual(action["res_model"], "subscription.contract")
        self.assertEqual(action["domain"], [("plan_id", "=", self.plan_monthly.id)])
