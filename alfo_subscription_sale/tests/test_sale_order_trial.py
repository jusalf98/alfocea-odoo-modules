from odoo import fields

from .common import AlfoSubscriptionSaleCommon


class TestSaleOrderTrial(AlfoSubscriptionSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)

    def test_trial_line_is_free_on_the_order(self):
        order = self._create_order([(self.product_trial, 2)])
        line = order.order_line
        self.assertTrue(line.subscription_trial)
        self.assertEqual(line.discount, 100.0)
        self.assertEqual(line.price_unit, 10.0)
        self.assertEqual(line.price_subtotal, 0.0)
        self.assertIn("Free trial: 14 days.", line.name)
        self.assertEqual(order.amount_untaxed, 0.0)

    def test_subscription_gets_the_real_price_and_pays_after_the_trial(self):
        order = self._create_order([(self.product_trial, 2)])
        self._confirm_as_salesman(order)
        contract = order.subscription_contract_ids
        self.assertEqual(contract.state, "trial")
        self.assertEqual(contract.line_ids.price_unit, 10.0)
        self.assertEqual(contract.amount_total, 20.0)
        self.assertNotIn("Free trial", contract.line_ids.name)
        # Nothing paid now: the first invoice is at the end of the trial.
        self.assertEqual(contract.next_invoice_date, contract.trial_end_date)

    def test_confirmed_order_keeps_its_discount(self):
        order = self._create_order([(self.product_trial, 1)])
        self._confirm_as_salesman(order)
        line = order.order_line
        line.subscription_trial = False
        line.discount = 15.0
        # Recomputing the trial flag of a confirmed order never flags it again.
        line._compute_subscription_trial()
        self.assertFalse(line.subscription_trial)
        self.assertEqual(line.discount, 15.0)

    def test_no_trial_for_plans_without_trial_days(self):
        order = self._create_order([(self.product_subscription, 1)])
        self.assertFalse(order.order_line.subscription_trial)
        self.assertEqual(order.order_line.discount, 0.0)

    def test_no_trial_when_the_customer_buys_the_product_again(self):
        first_order = self._create_order([(self.product_trial, 1)])
        self._confirm_as_salesman(first_order)
        second_order = self._create_order([(self.product_trial, 1)])
        self.assertFalse(second_order.order_line.subscription_trial)
        self.assertEqual(second_order.order_line.price_subtotal, 10.0)

    def test_no_trial_when_added_to_an_existing_subscription(self):
        self.plan_trial.group_by_partner = True
        other_trial_product = self.env["product.product"].create(
            {
                "name": "Music",
                "list_price": 5.0,
                "default_plan_id": self.plan_trial.id,
            }
        )
        first_order = self._create_order([(self.product_trial, 1)])
        self._confirm_as_salesman(first_order)
        second_order = self._create_order([(other_trial_product, 1)])
        self.assertFalse(second_order.order_line.subscription_trial)
        self._confirm_as_salesman(second_order)
        self.assertEqual(
            first_order.subscription_contract_ids,
            second_order.subscription_contract_ids,
        )

    def test_trial_line_and_paid_line_in_the_same_order(self):
        first_order = self._create_order([(self.product_subscription, 1)])
        self._confirm_as_salesman(first_order)
        monthly_contract = first_order.subscription_contract_ids
        next_date = monthly_contract.next_invoice_date

        order = self._create_order(
            [(self.product_subscription, 1), (self.product_trial, 1)]
        )
        self._confirm_as_salesman(order)

        # The monthly product was bought again: paid, added to its subscription.
        self.assertEqual(monthly_contract.line_ids.quantity, 2)
        self.assertEqual(monthly_contract.next_invoice_date, next_date)
        # The trial product starts a new subscription, paid after the trial.
        trial_contract = order.subscription_contract_ids - monthly_contract
        self.assertEqual(trial_contract.state, "trial")
        self.assertEqual(
            trial_contract.next_invoice_date, trial_contract.trial_end_date
        )
