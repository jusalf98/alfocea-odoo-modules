from dateutil.relativedelta import relativedelta

from .common import AlfoSubscriptionPurchaseCommon


class TestRecurringPurchaseOrder(AlfoSubscriptionPurchaseCommon):
    def _run_cron(self):
        self.SubscriptionContract._cron_create_recurring_purchase_orders()

    def test_due_contract_creates_confirmed_purchase_order(self):
        contract = self._create_running_contract(self.today)
        self._run_cron()

        order = contract.purchase_order_ids
        self.assertEqual(len(order), 1)
        self.assertEqual(order.state, "purchase")
        self.assertEqual(order.partner_id, self.vendor)
        self.assertEqual(order.origin, contract.name)
        self.assertEqual(order.order_line.product_id, self.product_license)
        self.assertEqual(order.order_line.product_qty, 3)
        # Contract price, not the product cost (50)
        self.assertEqual(order.order_line.price_unit, 40.0)
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
        self.assertEqual(len(contract.purchase_order_ids), 1)

    def test_contract_not_due_yet(self):
        contract = self._create_running_contract(self.today)
        contract.next_invoice_date = self.today + relativedelta(days=1)
        self._run_cron()
        self.assertFalse(contract.purchase_order_ids)

    def test_missed_periods_are_caught_up(self):
        contract = self._create_running_contract(self.today - relativedelta(months=2))
        self._run_cron()
        self.assertEqual(len(contract.purchase_order_ids), 3)

    def test_rfq_when_auto_confirm_disabled(self):
        self.plan_monthly.purchase_order_auto_confirm = False
        contract = self._create_running_contract(self.today)
        self._run_cron()
        self.assertEqual(contract.purchase_order_ids.state, "draft")

    def test_paused_and_customer_contracts_are_ignored(self):
        paused = self._create_running_contract(self.today)
        paused.action_pause()
        customer = self._create_running_contract(self.today, contract_type="sale")
        self._run_cron()
        self.assertFalse(paused.purchase_order_ids)
        self.assertFalse(customer.purchase_order_ids)

    def test_buyer_from_origin_order(self):
        order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(order)
        contract = order.subscription_contract_ids
        contract.next_invoice_date = self.today
        self._run_cron()
        renewal = contract.purchase_order_ids - order
        self.assertEqual(len(renewal), 1)
        self.assertEqual(renewal.user_id, self.buyer)
