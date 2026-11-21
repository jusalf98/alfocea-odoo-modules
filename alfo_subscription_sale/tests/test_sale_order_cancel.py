from .common import AlfoSubscriptionSaleCommon


class TestSaleOrderCancel(AlfoSubscriptionSaleCommon):
    def _first_subscription(self, quantity=1):
        order = self._create_order([(self.product_subscription, quantity)])
        self._confirm_as_salesman(order)
        return order, order.subscription_contract_ids

    def test_cancel_reverts_added_quantity(self):
        _first_order, contract = self._first_subscription()
        order = self._create_order([(self.product_subscription, 12)])
        self._confirm_as_salesman(order)
        self.assertEqual(contract.line_ids.quantity, 13)

        order.with_user(self.salesman)._action_cancel()

        self.assertEqual(contract.line_ids.quantity, 1)
        self.assertNotIn(order, contract.sale_order_ids)
        self.assertEqual(contract.state, "active")
        self.assertIn(
            "was cancelled, its changes were reverted", contract.message_ids[0].body
        )
        self.assertTrue(
            all(
                contract.order_change_ids.filtered(
                    lambda c: c.order_name == order.name
                ).mapped("reverted")
            )
        )

    def test_cancel_cancels_the_subscription_it_created(self):
        order, contract = self._first_subscription()
        order._action_cancel()
        self.assertEqual(contract.state, "cancelled")
        self.assertFalse(contract.line_ids)
        self.assertFalse(contract.sale_order_ids)

    def test_cancel_removes_the_line_it_added(self):
        self.plan_monthly.group_by_partner = True
        _first_order, contract = self._first_subscription()
        order = self._create_order([(self.product_hours, 2)])
        self._confirm_as_salesman(order)
        self.assertEqual(len(contract.line_ids), 2)

        order._action_cancel()

        self.assertEqual(contract.line_ids.product_id, self.product_subscription)
        self.assertEqual(contract.state, "active")

    def test_subscription_kept_when_other_orders_added_to_it(self):
        first_order, contract = self._first_subscription(quantity=1)
        second_order = self._create_order([(self.product_subscription, 2)])
        self._confirm_as_salesman(second_order)

        first_order._action_cancel()

        # The quantity of the second order remains: the subscription goes on.
        self.assertEqual(contract.line_ids.quantity, 2)
        self.assertEqual(contract.state, "active")
        self.assertEqual(contract.sale_order_ids, second_order)

    def test_cancel_and_confirm_again_applies_once(self):
        _first_order, contract = self._first_subscription()
        order = self._create_order([(self.product_subscription, 12)])
        self._confirm_as_salesman(order)
        order._action_cancel()
        order.action_draft()
        self._confirm_as_salesman(order)
        self.assertEqual(contract.line_ids.quantity, 13)

    def test_cancel_twice_reverts_once(self):
        _first_order, contract = self._first_subscription()
        order = self._create_order([(self.product_subscription, 5)])
        self._confirm_as_salesman(order)
        order._action_cancel()
        order._revert_subscription_changes()
        self.assertEqual(contract.line_ids.quantity, 1)

    def test_cancelling_a_quotation_changes_nothing(self):
        _first_order, contract = self._first_subscription()
        quotation = self._create_order([(self.product_subscription, 3)])
        quotation._action_cancel()
        self.assertEqual(contract.line_ids.quantity, 1)
