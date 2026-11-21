from odoo import Command
from odoo.tests import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class AlfoSubscriptionSaleCommon(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SubscriptionContract = cls.env["subscription.contract"]
        Plan = cls.env["subscription.plan"]
        cls.plan_monthly = Plan.create({"name": "Monthly", "periodicity": "monthly"})
        cls.plan_trial = Plan.create(
            {"name": "Monthly trial", "periodicity": "monthly", "trial_days": 14}
        )
        Product = cls.env["product.product"]
        cls.product_subscription = Product.create(
            {
                "name": "Coffee Box",
                "list_price": 30.0,
                "default_plan_id": cls.plan_monthly.id,
            }
        )
        cls.product_trial = Product.create(
            {
                "name": "Streaming",
                "list_price": 10.0,
                "default_plan_id": cls.plan_trial.id,
            }
        )
        # Same plan as product_subscription, different product.
        cls.product_hours = Product.create(
            {
                "name": "Consulting Hours",
                "list_price": 12.0,
                "default_plan_id": cls.plan_monthly.id,
            }
        )
        cls.product_regular = Product.create({"name": "Mug", "list_price": 8.0})
        cls.customer = cls.env["res.partner"].create({"name": "Coffee Shop"})
        # Salesman without any subscription access right: the contract creation
        # must work anyway (it runs as superuser).
        cls.salesman = new_test_user(
            cls.env,
            login="sub_salesman",
            groups="base.group_user,sales_team.group_sale_salesman",
        )

    @classmethod
    def _create_order(cls, product_qty_list, partner=None, **extra_vals):
        return cls.env["sale.order"].create(
            {
                "partner_id": (partner or cls.customer).id,
                "user_id": cls.salesman.id,
                "order_line": [
                    Command.create({"product_id": product.id, "product_uom_qty": qty})
                    for product, qty in product_qty_list
                ],
                **extra_vals,
            }
        )

    @classmethod
    def _create_running_contract(cls, date_start, plan=None, price_unit=22.0, **vals):
        """Customer subscription created by hand (not from an order), started."""
        contract = cls.SubscriptionContract.create(
            {
                "partner_id": cls.customer.id,
                "plan_id": (plan or cls.plan_monthly).id,
                "date_start": date_start,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_subscription.id,
                            "quantity": 2,
                            "price_unit": price_unit,
                        }
                    )
                ],
                **vals,
            }
        )
        contract.action_start()
        return contract

    def _confirm_as_salesman(self, orders):
        orders.with_user(self.salesman).action_confirm()

    def _contracts_of(self, partner=None):
        return self.SubscriptionContract.search(
            [("partner_id", "=", (partner or self.customer).id)]
        )
