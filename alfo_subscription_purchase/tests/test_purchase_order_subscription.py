from odoo.exceptions import ValidationError

from .common import AlfoSubscriptionPurchaseCommon


class TestPurchaseOrderSubscription(AlfoSubscriptionPurchaseCommon):
    def test_confirm_creates_and_starts_vendor_contract(self):
        order = self._create_order(
            [(self.product_license, 2, 45.0), (self.product_regular, 10, 3.0)]
        )
        self._confirm_as_buyer(order)

        contract = self._contracts_of()
        self.assertEqual(len(contract), 1)
        self.assertEqual(contract.contract_type, "purchase")
        self.assertTrue(contract.name.startswith("PSUB/"))
        self.assertEqual(contract.renewal_document, "purchase_order")
        self.assertEqual(contract.plan_id, self.plan_yearly)
        self.assertEqual(contract.state, "active")
        self.assertEqual(contract.line_ids.product_id, self.product_license)
        self.assertEqual(contract.line_ids.quantity, 2)
        self.assertEqual(contract.line_ids.price_unit, 45.0)
        # The confirmed order covers the first period: next one in a year.
        self.assertEqual(
            contract.next_invoice_date,
            self.plan_yearly._get_next_date(contract.date_start),
        )
        self.assertEqual(contract.purchase_order_ids, order)
        self.assertEqual(order.subscription_contract_ids, contract)

    def test_trial_plan_first_renewal_after_trial_and_paid_period(self):
        """The vendor charges the order: it covers the first period after the
        trial, so the first renewal is one period after the end of the trial."""
        self.plan_yearly.trial_days = 30
        order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(order)
        contract = self._contracts_of()
        self.assertEqual(contract.state, "trial")
        self.assertEqual(
            contract.next_invoice_date,
            self.plan_yearly._get_next_date(contract.trial_end_date),
        )

    def test_preview_wizard_before_confirming(self):
        first_order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(first_order)
        contract = self._contracts_of()
        order = self._create_order([(self.product_license, 4, 45.0)])

        action = (
            order.with_user(self.buyer)
            .with_context(subscription_preview=True)
            .button_confirm()
        )

        self.assertEqual(action["res_model"], "subscription.order.confirm")
        self.assertEqual(order.state, "draft")
        wizard = self.env["subscription.order.confirm"].browse(action["res_id"])
        self.assertEqual(wizard.line_ids.total_quantity, 5)
        wizard.with_user(self.buyer).action_confirm()
        self.assertEqual(order.state, "purchase")
        self.assertEqual(contract.line_ids.quantity, 5)

    def test_confirm_without_adding(self):
        first_order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(first_order)
        contract = self._contracts_of()
        order = self._create_order([(self.product_license, 4, 45.0)])
        action = (
            order.with_user(self.buyer)
            .with_context(subscription_preview=True)
            .button_confirm()
        )
        wizard = self.env["subscription.order.confirm"].browse(action["res_id"])
        wizard.with_user(self.buyer).action_confirm_without_adding()
        self.assertEqual(order.state, "purchase")
        self.assertEqual(contract.line_ids.quantity, 1)
        self.assertFalse(order.subscription_contract_ids)

    def test_cancel_reverts_the_subscription_changes(self):
        first_order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(first_order)
        contract = self._contracts_of()
        order = self._create_order([(self.product_license, 4, 45.0)])
        self._confirm_as_buyer(order)
        self.assertEqual(contract.line_ids.quantity, 5)

        order.with_user(self.buyer).button_cancel()

        self.assertEqual(contract.line_ids.quantity, 1)
        self.assertEqual(contract.purchase_order_ids, first_order)
        first_order.button_cancel()
        self.assertEqual(contract.state, "cancelled")

    def test_order_without_subscription_products(self):
        order = self._create_order([(self.product_regular, 5, 3.0)])
        self._confirm_as_buyer(order)
        self.assertFalse(self._contracts_of())

    def test_sale_plan_does_not_create_vendor_contract(self):
        order = self._create_order([(self.product_sale_plan, 1, 10.0)])
        self._confirm_as_buyer(order)
        self.assertFalse(self._contracts_of())

    def test_existing_open_contract_is_reused(self):
        first_order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(first_order)
        contract = self._contracts_of()
        second_order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(second_order)
        self.assertEqual(self._contracts_of(), contract)
        self.assertEqual(contract.purchase_order_ids, first_order | second_order)
        self.assertEqual(contract.line_ids.quantity, 2)

    def test_new_product_same_plan_creates_new_subscription(self):
        first_order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(first_order)
        first_contract = self._contracts_of()
        second_order = self._create_order([(self.product_support, 1, 20.0)])
        self._confirm_as_buyer(second_order)
        second_contract = self._contracts_of() - first_contract
        self.assertEqual(second_contract.line_ids.product_id, self.product_support)
        self.assertEqual(second_order.subscription_contract_ids, second_contract)
        self.assertEqual(first_contract.purchase_order_ids, first_order)

    def test_new_product_added_when_plan_groups_by_partner(self):
        self.plan_yearly.group_by_partner = True
        first_order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(first_order)
        contract = self._contracts_of()
        second_order = self._create_order([(self.product_support, 1, 20.0)])
        self._confirm_as_buyer(second_order)
        self.assertEqual(self._contracts_of(), contract)
        self.assertEqual(
            contract.line_ids.product_id, self.product_license | self.product_support
        )

    def test_discount_is_applied_to_contract_price(self):
        order = self._create_order([(self.product_license, 1, 100.0)])
        order.order_line.discount = 20.0
        self._confirm_as_buyer(order)
        self.assertAlmostEqual(self._contracts_of().line_ids.price_unit, 80.0)

    def test_purchase_order_renewal_only_for_vendor_contracts(self):
        contract = self.SubscriptionContract.create(
            {"partner_id": self.vendor.id, "plan_id": self.plan_monthly.id}
        )
        self.assertEqual(contract.contract_type, "sale")
        with self.assertRaises(ValidationError):
            contract.renewal_document = "purchase_order"

    def test_smart_buttons(self):
        order = self._create_order([(self.product_license, 1, 45.0)])
        self._confirm_as_buyer(order)
        contract = order.subscription_contract_ids
        self.assertEqual(
            order.action_view_subscription_contracts()["res_id"], contract.id
        )
        self.assertEqual(contract.action_view_purchase_orders()["res_id"], order.id)
