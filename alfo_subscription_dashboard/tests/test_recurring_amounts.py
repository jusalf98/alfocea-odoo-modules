from odoo import Command, fields

from odoo.addons.base.tests.common import BaseCommon


class TestRecurringAmounts(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Contract = cls.env["subscription.contract"]
        cls.today = fields.Date.context_today(cls.Contract)
        cls.partner = cls.env["res.partner"].create({"name": "Analysis Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Analysis Box", "list_price": 120.0}
        )

    def _contract(self, periodicity, interval=1, **vals):
        plan = self.env["subscription.plan"].create(
            {"name": periodicity, "periodicity": periodicity, "interval": interval}
        )
        return self.Contract.create(
            {
                "partner_id": self.partner.id,
                "plan_id": plan.id,
                "date_start": self.today,
                "line_ids": [Command.create({"product_id": self.product.id})],
                **vals,
            }
        )

    def test_mrr_by_periodicity(self):
        cases = [
            ("monthly", 1, 120.0),
            ("monthly", 3, 40.0),
            ("yearly", 1, 10.0),
            ("weekly", 1, round(120 * 52 / 12, 2)),
            ("daily", 30, round(120 * 365 / 12 / 30, 2)),
        ]
        for periodicity, interval, mrr in cases:
            with self.subTest(periodicity=periodicity, interval=interval):
                contract = self._contract(periodicity, interval)
                self.assertAlmostEqual(contract.recurring_monthly, mrr, places=2)
                self.assertAlmostEqual(
                    contract.recurring_yearly, round(mrr * 12, 2), delta=0.05
                )

    def test_mrr_follows_the_lines(self):
        contract = self._contract("monthly")
        contract.line_ids.quantity = 2
        self.assertEqual(contract.recurring_monthly, 240.0)

    def test_mrr_aggregated_by_plan(self):
        monthly = self._contract("monthly")
        yearly = self._contract("yearly")
        (monthly | yearly).action_start()
        groups = self.Contract._read_group(
            [("id", "in", (monthly | yearly).ids), ("state", "=", "active")],
            [],
            ["recurring_monthly:sum"],
        )
        self.assertEqual(groups[0][0], 130.0)

    def test_analysis_views_load(self):
        for xml_id in (
            "alfo_subscription_dashboard.subscription_contract_view_pivot",
            "alfo_subscription_dashboard.subscription_contract_view_graph",
        ):
            view = self.env.ref(xml_id)
            self.assertTrue(self.Contract.get_view(view.id)["arch"])
        for xml_id in (
            "alfo_subscription_dashboard.subscription_mrr_action",
            "alfo_subscription_dashboard.subscription_new_action",
            "alfo_subscription_dashboard.subscription_churn_action",
            "alfo_subscription_dashboard.subscription_vendor_cost_action",
        ):
            action = self.env["ir.actions.act_window"]._for_xml_id(xml_id)
            self.assertEqual(action["res_model"], "subscription.contract")
