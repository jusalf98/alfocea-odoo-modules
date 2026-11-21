from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionLabels(AlfoSubscriptionCoreCommon):
    def test_billing_label(self):
        plan = self.plan_monthly
        cases = [
            ("monthly", 1, "every month"),
            ("monthly", 3, "every 3 months"),
            ("weekly", 1, "every week"),
            ("weekly", 2, "every 2 weeks"),
            ("daily", 15, "every 15 days"),
            ("yearly", 1, "every year"),
        ]
        for periodicity, interval, label in cases:
            with self.subTest(periodicity=periodicity, interval=interval):
                plan.write({"periodicity": periodicity, "interval": interval})
                self.assertEqual(plan.billing_label, label)

    def test_trial_label(self):
        self.assertEqual(self.plan_monthly.trial_label, "")
        self.plan_monthly.trial_days = 1
        self.assertEqual(self.plan_monthly.trial_label, "1 day")
        self.assertEqual(self.plan_trial.trial_label, "15 days")
