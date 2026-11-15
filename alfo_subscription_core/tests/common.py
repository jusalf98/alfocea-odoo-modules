from odoo import Command

from odoo.addons.base.tests.common import BaseCommon


class AlfoSubscriptionCoreCommon(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SubscriptionPlan = cls.env["subscription.plan"]
        cls.SubscriptionContract = cls.env["subscription.contract"]
        Partner = cls.env["res.partner"]
        cls.partner = Partner.create({"name": "Subscription Customer"})
        cls.vendor = Partner.create({"name": "Subscription Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "Monthly Box", "list_price": 25.0, "standard_price": 15.0}
        )
        cls.plan_monthly = cls._create_plan("Monthly")
        cls.plan_trial = cls._create_plan("Monthly with trial", trial_days=15)

    @classmethod
    def _create_plan(cls, name, **extra_vals):
        return cls.SubscriptionPlan.create(
            {"name": name, "periodicity": "monthly", "interval": 1, **extra_vals}
        )

    @classmethod
    def _create_contract(cls, plan, date_start, quantity=1.0, **extra_vals):
        return cls.SubscriptionContract.create(
            {
                "partner_id": cls.partner.id,
                "plan_id": plan.id,
                "date_start": date_start,
                "line_ids": [
                    Command.create({"product_id": cls.product.id, "quantity": quantity})
                ],
                **extra_vals,
            }
        )
