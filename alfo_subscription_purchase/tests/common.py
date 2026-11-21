from odoo import Command, fields
from odoo.tests import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class AlfoSubscriptionPurchaseCommon(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SubscriptionContract = cls.env["subscription.contract"]
        cls.today = fields.Date.context_today(cls.SubscriptionContract)
        Plan = cls.env["subscription.plan"]
        cls.plan_monthly = Plan.create({"name": "Monthly", "periodicity": "monthly"})
        cls.plan_yearly = Plan.create({"name": "Yearly", "periodicity": "yearly"})
        Product = cls.env["product.product"]
        cls.product_license = Product.create(
            {
                "name": "Software License",
                "standard_price": 50.0,
                "purchase_plan_id": cls.plan_yearly.id,
            }
        )
        # Same vendor plan as product_license, different product.
        cls.product_support = Product.create(
            {
                "name": "Support Contract",
                "standard_price": 20.0,
                "purchase_plan_id": cls.plan_yearly.id,
            }
        )
        # Sold with a plan, but its vendor subscription plan is empty.
        cls.product_sale_plan = Product.create(
            {"name": "Coffee Box", "default_plan_id": cls.plan_monthly.id}
        )
        cls.product_regular = Product.create({"name": "Paper", "standard_price": 3.0})
        cls.vendor = cls.env["res.partner"].create({"name": "Cloud Hosting"})
        # Buyer without any subscription access right: the contract creation
        # must work anyway (it runs as superuser).
        cls.buyer = new_test_user(
            cls.env,
            login="sub_buyer",
            groups="base.group_user,purchase.group_purchase_user",
        )

    @classmethod
    def _create_order(cls, product_qty_price_list, partner=None):
        return cls.env["purchase.order"].create(
            {
                "partner_id": (partner or cls.vendor).id,
                "user_id": cls.buyer.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": price,
                        }
                    )
                    for product, qty, price in product_qty_price_list
                ],
            }
        )

    @classmethod
    def _create_running_contract(cls, date_start, plan=None, **vals):
        """Vendor subscription created by hand (not from an order), started."""
        contract = cls.SubscriptionContract.create(
            {
                "contract_type": "purchase",
                "partner_id": cls.vendor.id,
                "plan_id": (plan or cls.plan_monthly).id,
                "date_start": date_start,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_license.id,
                            "quantity": 3,
                            "price_unit": 40.0,
                        }
                    )
                ],
                **vals,
            }
        )
        contract.action_start()
        return contract

    def _confirm_as_buyer(self, orders):
        orders.with_user(self.buyer).button_confirm()

    def _contracts_of(self, partner=None):
        return self.SubscriptionContract.search(
            [("partner_id", "=", (partner or self.vendor).id)]
        )
