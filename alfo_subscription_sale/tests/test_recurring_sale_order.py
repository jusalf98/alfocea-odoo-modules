from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tools import mute_logger

from .common import AlfoSubscriptionSaleCommon


class TestRecurringSaleOrder(AlfoSubscriptionSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)

    def _run_cron(self):
        self.SubscriptionContract._cron_create_recurring_sale_orders()

    def test_due_contract_creates_confirmed_order(self):
        contract = self._create_running_contract(self.today)
        self.assertEqual(contract.next_invoice_date, self.today)

        self._run_cron()

        order = contract.sale_order_ids
        self.assertEqual(len(order), 1)
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.partner_id, self.customer)
        self.assertEqual(order.origin, contract.name)
        self.assertEqual(order.order_line.product_id, self.product_subscription)
        self.assertEqual(order.order_line.product_uom_qty, 2)
        # Contract price, not the product list price (30)
        self.assertEqual(order.order_line.price_unit, 22.0)
        self.assertIn("Period:", order.order_line.name)
        self.assertEqual(
            contract.next_invoice_date, self.today + relativedelta(months=1)
        )
        # Confirming the renewal order does not create another subscription
        self.assertEqual(self._contracts_of(), contract)

    def test_cron_is_idempotent(self):
        contract = self._create_running_contract(self.today)
        self._run_cron()
        self._run_cron()
        self.assertEqual(len(contract.sale_order_ids), 1)

    def test_contract_not_due_yet(self):
        contract = self._create_running_contract(self.today)
        contract.next_invoice_date = self.today + relativedelta(days=1)
        self._run_cron()
        self.assertFalse(contract.sale_order_ids)

    def test_paused_and_draft_contracts_are_ignored(self):
        paused = self._create_running_contract(self.today)
        paused.action_pause()
        draft = self._create_running_contract(self.today)
        draft.action_cancel()
        draft.action_set_draft()
        draft.next_invoice_date = self.today
        self._run_cron()
        self.assertFalse(paused.sale_order_ids)
        self.assertFalse(draft.sale_order_ids)

    def test_finished_trial_is_renewed(self):
        contract = self._create_running_contract(self.today, plan=self.plan_trial)
        self.assertEqual(contract.state, "trial")
        contract.next_invoice_date = self.today  # trial ends today
        self._run_cron()
        self.assertEqual(len(contract.sale_order_ids), 1)

    def test_missed_periods_are_caught_up(self):
        contract = self._create_running_contract(self.today - relativedelta(months=2))
        self._run_cron()
        self.assertEqual(len(contract.sale_order_ids), 3)
        self.assertEqual(
            contract.next_invoice_date, self.today + relativedelta(months=1)
        )

    def test_no_order_after_end_date(self):
        start = self.today - relativedelta(months=2)
        contract = self._create_running_contract(
            start, date_end=start + relativedelta(months=1, days=-1)
        )
        self._run_cron()
        self.assertEqual(len(contract.sale_order_ids), 1)

    def test_quotation_when_auto_confirm_disabled(self):
        self.plan_monthly.sale_order_auto_confirm = False
        contract = self._create_running_contract(self.today)
        self._run_cron()
        self.assertEqual(contract.sale_order_ids.state, "draft")

    def test_vendor_subscriptions_are_ignored(self):
        contract = self._create_running_contract(self.today, contract_type="purchase")
        self._run_cron()
        self.assertFalse(contract.sale_order_ids)

    def test_salesperson_from_origin_order(self):
        order = self._create_order([(self.product_subscription, 1)])
        self._confirm_as_salesman(order)
        contract = order.subscription_contract_ids
        contract.next_invoice_date = self.today
        self._run_cron()
        renewal = contract.sale_order_ids - order
        self.assertEqual(len(renewal), 1)
        self.assertEqual(renewal.user_id, self.salesman)

    @mute_logger("odoo.addons.alfo_subscription_core.models.subscription_contract")
    def test_error_in_one_contract_does_not_block_others(self):
        failing = self._create_running_contract(self.today)
        healthy = self._create_running_contract(self.today)
        Contract = type(self.SubscriptionContract)
        original = Contract._prepare_renewal_sale_order_vals

        def prepare_vals(contract, *args):
            if contract == failing:
                raise ValueError("Broken subscription")
            return original(contract, *args)

        with patch.object(Contract, "_prepare_renewal_sale_order_vals", prepare_vals):
            self._run_cron()

        self.assertFalse(failing.sale_order_ids)
        self.assertEqual(failing.next_invoice_date, self.today)
        self.assertEqual(len(healthy.sale_order_ids), 1)
