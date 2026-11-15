from odoo import Command

from .common import AlfoSubscriptionSaleCommon


class TestSaleOrderSubscription(AlfoSubscriptionSaleCommon):
    def test_confirm_creates_and_starts_contract(self):
        order = self._create_order(
            [(self.product_subscription, 2), (self.product_regular, 1)]
        )
        self._confirm_as_salesman(order)

        contract = self._contracts_of()
        self.assertEqual(len(contract), 1)
        self.assertEqual(contract.contract_type, "sale")
        self.assertEqual(contract.plan_id, self.plan_monthly)
        self.assertEqual(contract.company_id, order.company_id)
        self.assertEqual(contract.state, "active")
        # The confirmed order covers the first period: next one in a month.
        self.assertEqual(
            contract.next_invoice_date,
            self.plan_monthly._get_next_date(contract.date_start),
        )
        self.assertEqual(contract.line_ids.product_id, self.product_subscription)
        self.assertEqual(contract.line_ids.quantity, 2)
        self.assertEqual(contract.line_ids.price_unit, 30.0)
        self.assertEqual(contract.sale_order_ids, order)
        self.assertEqual(order.subscription_contract_ids, contract)
        self.assertEqual(order.subscription_contract_count, 1)
        self.assertIn(order.name, contract.message_ids[0].body)

    def test_trial_plan_starts_in_trial(self):
        order = self._create_order([(self.product_trial, 1)])
        self._confirm_as_salesman(order)
        contract = self._contracts_of()
        self.assertEqual(contract.state, "trial")
        self.assertEqual(contract.next_invoice_date, contract.trial_end_date)

    def test_order_without_subscription_products(self):
        order = self._create_order([(self.product_regular, 3)])
        self._confirm_as_salesman(order)
        self.assertFalse(self._contracts_of())
        self.assertFalse(order.subscription_contract_ids)

    def test_one_contract_per_plan(self):
        order = self._create_order(
            [
                (self.product_subscription, 1),
                (self.product_trial, 1),
                (self.product_subscription, 3),
            ]
        )
        self._confirm_as_salesman(order)
        contracts = self._contracts_of()
        self.assertEqual(len(contracts), 2)
        monthly = contracts.filtered(lambda c: c.plan_id == self.plan_monthly)
        self.assertEqual(len(monthly.line_ids), 2)
        self.assertEqual(order.subscription_contract_ids, contracts)

    def test_existing_open_contract_is_reused(self):
        first_order = self._create_order([(self.product_subscription, 1)])
        self._confirm_as_salesman(first_order)
        contract = self._contracts_of()

        second_order = self._create_order([(self.product_subscription, 5)])
        self._confirm_as_salesman(second_order)

        self.assertEqual(self._contracts_of(), contract)
        self.assertEqual(contract.sale_order_ids, first_order | second_order)
        self.assertEqual(contract.line_ids.quantity, 1)

    def test_closed_contract_is_not_reused(self):
        first_order = self._create_order([(self.product_subscription, 1)])
        self._confirm_as_salesman(first_order)
        old_contract = self._contracts_of()
        old_contract.action_cancel()

        second_order = self._create_order([(self.product_subscription, 1)])
        self._confirm_as_salesman(second_order)

        new_contract = self._contracts_of() - old_contract
        self.assertEqual(len(new_contract), 1)
        self.assertEqual(new_contract.state, "active")
        self.assertEqual(new_contract.sale_order_ids, second_order)

    def test_vendor_contract_is_not_reused(self):
        self.SubscriptionContract.create(
            {
                "contract_type": "purchase",
                "partner_id": self.customer.id,
                "plan_id": self.plan_monthly.id,
            }
        )
        order = self._create_order([(self.product_subscription, 1)])
        self._confirm_as_salesman(order)
        sale_contracts = self._contracts_of().filtered(
            lambda c: c.contract_type == "sale"
        )
        self.assertEqual(len(sale_contracts), 1)

    def test_same_customer_orders_confirmed_together(self):
        orders = self._create_order([(self.product_subscription, 1)])
        orders |= self._create_order([(self.product_subscription, 2)])
        self._confirm_as_salesman(orders)
        contract = self._contracts_of()
        self.assertEqual(len(contract), 1)
        self.assertEqual(contract.sale_order_ids, orders)

    def test_discount_is_applied_to_contract_price(self):
        order = self._create_order([(self.product_subscription, 1)])
        order.order_line.discount = 10.0
        self._confirm_as_salesman(order)
        self.assertAlmostEqual(self._contracts_of().line_ids.price_unit, 27.0)

    def test_section_lines_are_ignored(self):
        order = self._create_order([(self.product_subscription, 1)])
        order.order_line = [
            Command.create({"display_type": "line_section", "name": "Subscriptions"})
        ]
        self._confirm_as_salesman(order)
        self.assertEqual(len(self._contracts_of().line_ids), 1)

    def test_smart_buttons(self):
        order = self._create_order(
            [(self.product_subscription, 1), (self.product_trial, 1)]
        )
        self._confirm_as_salesman(order)
        action = order.action_view_subscription_contracts()
        self.assertEqual(
            action["domain"], [("id", "in", order.subscription_contract_ids.ids)]
        )
        contract = order.subscription_contract_ids[0]
        action = contract.action_view_sale_orders()
        self.assertEqual(action["res_id"], order.id)
