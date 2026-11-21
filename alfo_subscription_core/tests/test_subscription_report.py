from odoo import fields

from .common import AlfoSubscriptionCoreCommon

REPORT = "alfo_subscription_core.report_subscription_contract"


class TestSubscriptionReport(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)

    def _render(self, contracts):
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            REPORT, contracts.ids
        )
        return html.decode()

    def test_customer_subscription_report(self):
        contract = self._create_contract(self.plan_trial, self.today, quantity=2)
        contract.note = "<p>Cancel at any time.</p>"
        contract.action_start()
        html = self._render(contract)
        self.assertIn("Customer Subscription", html)
        self.assertIn(contract.name, html)
        self.assertIn(self.partner.name, html)
        self.assertIn(self.plan_trial.name, html)
        self.assertIn(self.product.display_name, html)
        self.assertIn("Free Trial Until", html)
        self.assertIn("Cancel at any time.", html)

    def test_vendor_subscription_report(self):
        contract = self._create_contract(
            self.plan_monthly, self.today, contract_type="purchase"
        )
        html = self._render(contract)
        self.assertIn("Vendor Subscription", html)
        self.assertNotIn("Free Trial Until", html)
        self.assertNotIn("Terms and Conditions", html)

    def test_several_subscriptions_in_one_report(self):
        contracts = self._create_contract(self.plan_monthly, self.today)
        contracts |= self._create_contract(self.plan_trial, self.today)
        html = self._render(contracts)
        for contract in contracts:
            self.assertIn(contract.name, html)

    def test_report_is_in_the_print_menu(self):
        report = self.env.ref(
            "alfo_subscription_core.action_report_subscription_contract"
        )
        self.assertEqual(report.binding_model_id.model, "subscription.contract")
