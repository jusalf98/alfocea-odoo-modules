from .common import AlfoSubscriptionSaleCommon


class TestSaleOrderPreview(AlfoSubscriptionSaleCommon):
    def _confirm_from_form(self, order, user=None):
        """Same as the Confirm buttons of the form (they ask for a preview)."""
        order = order.with_user(user or self.salesman)
        return order.with_context(subscription_preview=True).action_confirm()

    def _first_subscription(self):
        order = self._create_order([(self.product_subscription, 1)])
        self._confirm_as_salesman(order)
        return order.subscription_contract_ids

    def test_preview_when_quantity_is_added(self):
        contract = self._first_subscription()
        order = self._create_order([(self.product_subscription, 2)])

        action = self._confirm_from_form(order)

        self.assertEqual(action["res_model"], "subscription.order.confirm")
        self.assertEqual(order.state, "draft")
        wizard = self.env["subscription.order.confirm"].browse(action["res_id"])
        self.assertEqual(len(wizard.line_ids), 1)
        line = wizard.line_ids
        self.assertEqual(line.contract_name, contract.name)
        self.assertEqual(line.change, "quantity")
        self.assertEqual(line.current_quantity, 1)
        self.assertEqual(line.added_quantity, 2)
        self.assertEqual(line.total_quantity, 3)

        wizard.with_user(self.salesman).action_confirm()

        self.assertEqual(order.state, "sale")
        self.assertEqual(contract.line_ids.quantity, 3)

    def test_preview_when_product_is_added_to_the_subscription(self):
        self.plan_monthly.group_by_partner = True
        contract = self._first_subscription()
        order = self._create_order([(self.product_hours, 1)])

        action = self._confirm_from_form(order)

        wizard = self.env["subscription.order.confirm"].browse(action["res_id"])
        changes = {line.product_id: line.change for line in wizard.line_ids}
        self.assertEqual(
            changes,
            {self.product_subscription: "current", self.product_hours: "new_line"},
        )
        wizard.action_confirm()
        self.assertEqual(len(contract.line_ids), 2)

    def test_confirm_without_adding(self):
        contract = self._first_subscription()
        order = self._create_order(
            [(self.product_subscription, 2), (self.product_trial, 1)]
        )
        action = self._confirm_from_form(order)
        wizard = self.env["subscription.order.confirm"].browse(action["res_id"])

        wizard.with_user(self.salesman).action_confirm_without_adding()

        self.assertEqual(order.state, "sale")
        # The existing subscription is not changed nor linked to the order.
        self.assertEqual(contract.line_ids.quantity, 1)
        self.assertNotIn(order, contract.sale_order_ids)
        self.assertIn("Confirmed without adding products", order.message_ids[0].body)
        self.assertIn(contract.name, order.message_ids[0].body)
        # The free trial product still gets its new subscription.
        new_contract = order.subscription_contract_ids
        self.assertEqual(new_contract.line_ids.product_id, self.product_trial)
        self.assertEqual(new_contract.state, "trial")

    def test_confirm_without_adding_a_new_product(self):
        self.plan_monthly.group_by_partner = True
        contract = self._first_subscription()
        order = self._create_order([(self.product_hours, 1)])
        action = self._confirm_from_form(order)
        wizard = self.env["subscription.order.confirm"].browse(action["res_id"])

        wizard.action_confirm_without_adding()

        self.assertEqual(order.state, "sale")
        self.assertEqual(contract.line_ids.product_id, self.product_subscription)
        self.assertFalse(order.subscription_contract_ids)

    def test_no_preview_for_a_new_subscription(self):
        order = self._create_order([(self.product_subscription, 1)])
        result = self._confirm_from_form(order)
        self.assertNotIsInstance(result, dict)
        self.assertEqual(order.state, "sale")
        self.assertTrue(order.subscription_contract_ids)

    def test_no_preview_in_automatic_confirmations(self):
        contract = self._first_subscription()
        order = self._create_order([(self.product_subscription, 2)])
        # Without the context of the form buttons (online payment, other modules)
        order.with_user(self.salesman).action_confirm()
        self.assertEqual(order.state, "sale")
        self.assertEqual(contract.line_ids.quantity, 3)
