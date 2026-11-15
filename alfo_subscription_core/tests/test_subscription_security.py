from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import new_test_user

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionSecurity(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = new_test_user(
            cls.env, login="sub_internal", groups="base.group_user"
        )
        # The subscription groups don't imply base.group_user: the access right
        # is granted explicitly to internal users.
        cls.subscription_user = new_test_user(
            cls.env,
            login="sub_user",
            groups="base.group_user,alfo_subscription_core.group_subscription_user",
        )
        cls.subscription_manager = new_test_user(
            cls.env,
            login="sub_manager",
            groups="base.group_user,alfo_subscription_core.group_subscription_manager",
        )
        cls.today = fields.Date.context_today(cls.SubscriptionContract)

    def test_odoo_admin_is_subscription_manager(self):
        admin = self.env.ref("base.user_admin")
        self.assertTrue(
            admin.has_group("alfo_subscription_core.group_subscription_manager")
        )
        self.assertTrue(
            admin.has_group("alfo_subscription_core.group_subscription_user")
        )

    def test_product_plan_only_for_managers(self):
        self.product.product_tmpl_id.default_plan_id = self.plan_monthly
        template = self.product.product_tmpl_id
        self.assertEqual(
            template.with_user(self.subscription_manager).default_plan_id,
            self.plan_monthly,
        )
        with self.assertRaises(AccessError):
            template.with_user(self.subscription_user).read(["default_plan_id"])

    def test_internal_user_has_no_access(self):
        with self.assertRaises(AccessError):
            self.SubscriptionContract.with_user(self.internal_user).search([])
        with self.assertRaises(AccessError):
            self.SubscriptionPlan.with_user(self.internal_user).search([])

    def test_user_manages_contracts_but_not_plans(self):
        Contract = self.SubscriptionContract.with_user(self.subscription_user)
        contract = Contract.create(
            {"partner_id": self.partner.id, "plan_id": self.plan_monthly.id}
        )
        self.assertTrue(contract.name.startswith("SUB/"))
        self.assertTrue(self.plan_monthly.with_user(self.subscription_user).name)
        with self.assertRaises(AccessError):
            self.SubscriptionPlan.with_user(self.subscription_user).create(
                {"name": "Forbidden"}
            )
        with self.assertRaises(AccessError):
            contract.unlink()

    def test_manager_has_full_access(self):
        plan = self.SubscriptionPlan.with_user(self.subscription_manager).create(
            {"name": "Yearly", "periodicity": "yearly"}
        )
        contract = self._create_contract(plan, self.today).with_user(
            self.subscription_manager
        )
        contract.unlink()
        plan.unlink()
        self.assertFalse(plan.exists())
