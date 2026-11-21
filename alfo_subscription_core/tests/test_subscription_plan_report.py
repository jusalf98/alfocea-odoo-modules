from odoo import fields

from .common import AlfoSubscriptionCoreCommon

REPORT = "alfo_subscription_core.report_subscription_plan"


class TestSubscriptionPlanReport(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)
        # Monthly plan: 2 running customer subscriptions (25 x 2 and 25 x 1),
        # 1 running vendor subscription (cost 15), 1 draft and 1 cancelled.
        cls.active_2 = cls._create_contract(cls.plan_monthly, cls.today, quantity=2)
        cls.active_1 = cls._create_contract(cls.plan_monthly, cls.today)
        cls.vendor = cls._create_contract(
            cls.plan_monthly, cls.today, contract_type="purchase"
        )
        (cls.active_2 | cls.active_1 | cls.vendor).action_start()
        cls.draft = cls._create_contract(cls.plan_monthly, cls.today)
        cls.cancelled = cls._create_contract(cls.plan_monthly, cls.today)
        cls.cancelled.action_cancel()

    def _render(self, plans):
        html, _report_type = self.env["ir.actions.report"]._render_qweb_html(
            REPORT, plans.ids
        )
        return html.decode()

    def test_report_contracts_exclude_finished_ones(self):
        contracts = self.plan_monthly._get_report_contracts()
        self.assertEqual(
            contracts, self.active_2 | self.active_1 | self.vendor | self.draft
        )

    def test_customers_are_listed_first(self):
        contracts = self.plan_monthly._get_report_contracts()
        self.assertEqual(contracts[-1], self.vendor)
        totals = self.plan_monthly._get_report_totals()
        self.assertEqual(
            [total["contract_type"] for total in totals], ["sale", "purchase"]
        )

    def test_report_totals_by_type(self):
        totals = {
            total["contract_type"]: total["amount"]
            for total in self.plan_monthly._get_report_totals()
        }
        # The draft subscription is listed but not added to the totals.
        self.assertEqual(totals, {"sale": 75.0, "purchase": 15.0})

    def test_plan_report_content(self):
        html = self._render(self.plan_monthly)
        self.assertIn("Subscription Plan", html)
        self.assertIn(self.plan_monthly.name, html)
        self.assertIn("No trial", html)
        for contract in self.active_2 | self.vendor | self.draft:
            self.assertIn(contract.name, html)
        self.assertNotIn(self.cancelled.name, html)
        self.assertIn("Customer subscriptions in progress", html)
        self.assertIn("Vendor subscriptions in progress", html)

    def test_plan_without_subscriptions(self):
        html = self._render(self.plan_trial)
        self.assertIn("No open subscription uses this plan.", html)
        self.assertIn("days", html)
        self.assertNotIn("in progress", html)

    def test_several_plans_in_one_report(self):
        html = self._render(self.plan_monthly | self.plan_trial)
        self.assertIn(self.plan_monthly.name, html)
        self.assertIn(self.plan_trial.name, html)

    def test_report_is_in_the_print_menu(self):
        report = self.env.ref("alfo_subscription_core.action_report_subscription_plan")
        self.assertEqual(report.binding_model_id.model, "subscription.plan")
