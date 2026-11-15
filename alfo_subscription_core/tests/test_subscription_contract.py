from datetime import date, timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionContract(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)

    def test_reference_from_sequence(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        self.assertTrue(contract.name.startswith("SUB/"))

    def test_line_defaults_and_total(self):
        contract = self._create_contract(self.plan_monthly, self.today, quantity=2)
        line = contract.line_ids
        self.assertEqual(line.name, self.product.display_name)
        self.assertEqual(line.price_unit, 25.0)
        self.assertEqual(line.price_subtotal, 50.0)
        self.assertEqual(contract.amount_total, 50.0)

    def test_line_quantity_must_be_positive(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        with self.assertRaises(ValidationError):
            contract.line_ids.quantity = 0

    def test_start_without_trial(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.action_start()
        self.assertEqual(contract.state, "active")
        self.assertFalse(contract.trial_end_date)
        self.assertEqual(contract.next_invoice_date, self.today)

    def test_start_with_trial(self):
        contract = self._create_contract(self.plan_trial, self.today)
        contract.action_start()
        trial_end = self.today + timedelta(days=15)
        self.assertEqual(contract.state, "trial")
        self.assertEqual(contract.trial_end_date, trial_end)
        self.assertEqual(contract.next_invoice_date, trial_end)

    def test_start_with_trial_already_finished(self):
        contract = self._create_contract(
            self.plan_trial, self.today - timedelta(days=30)
        )
        contract.action_start()
        self.assertEqual(contract.state, "active")
        self.assertEqual(contract.next_invoice_date, contract.date_start)

    def test_start_without_lines(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.line_ids.unlink()
        with self.assertRaises(UserError):
            contract.action_start()

    def test_state_flow(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.action_start()
        contract.action_pause()
        self.assertEqual(contract.state, "paused")
        contract.action_resume()
        self.assertEqual(contract.state, "active")
        contract.action_cancel()
        self.assertEqual(contract.state, "cancelled")
        contract.action_set_draft()
        self.assertEqual(contract.state, "draft")
        self.assertFalse(contract.next_invoice_date)

    def test_invalid_transition(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        with self.assertRaises(UserError):
            contract.action_pause()
        with self.assertRaises(UserError):
            contract.action_resume()

    def test_end_date_before_start_date(self):
        with self.assertRaises(ValidationError):
            self._create_contract(
                self.plan_monthly, date(2026, 5, 1), date_end=date(2026, 4, 1)
            )

    def test_plan_change_does_not_alter_running_trial(self):
        contract = self._create_contract(self.plan_trial, self.today)
        contract.action_start()
        trial_end = contract.trial_end_date
        self.plan_trial.trial_days = 60
        self.assertEqual(contract.trial_end_date, trial_end)

    def test_cron_update_states(self):
        trial_finished = self._create_contract(self.plan_trial, self.today)
        trial_finished.action_start()
        trial_finished.date_start = self.today - timedelta(days=20)
        trial_running = self._create_contract(self.plan_trial, self.today)
        trial_running.action_start()
        to_expire = self._create_contract(
            self.plan_monthly,
            self.today - timedelta(days=60),
            date_end=self.today - timedelta(days=1),
        )
        to_expire.action_start()

        self.SubscriptionContract._cron_update_states()

        self.assertEqual(trial_finished.state, "active")
        self.assertEqual(trial_running.state, "trial")
        self.assertEqual(to_expire.state, "expired")

    def test_group_by_state_shows_all_states(self):
        groups = self.SubscriptionContract.read_group([], ["state"], ["state"])
        self.assertEqual(
            [group["state"] for group in groups],
            ["draft", "trial", "active", "paused", "cancelled", "expired"],
        )
