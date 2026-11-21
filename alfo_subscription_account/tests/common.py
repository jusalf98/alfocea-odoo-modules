from odoo import Command, fields

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class AlfoSubscriptionAccountCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The accounting test base works with an accountant user, not as superuser.
        cls.env.user.sudo().groups_id = [
            Command.link(
                cls.env.ref("alfo_subscription_core.group_subscription_manager").id
            )
        ]
        cls.SubscriptionContract = cls.env["subscription.contract"]
        cls.today = fields.Date.context_today(cls.SubscriptionContract)
        cls.plan_monthly = cls.env["subscription.plan"].create(
            {"name": "Monthly", "periodicity": "monthly"}
        )

    @classmethod
    def _create_running_contract(cls, date_start, contract_type="sale", **vals):
        # Renewed with invoices, whatever other integration module is installed.
        vals.setdefault("renewal_document", "invoice")
        contract = cls.SubscriptionContract.create(
            {
                "contract_type": contract_type,
                "partner_id": cls.partner_a.id,
                "plan_id": cls.plan_monthly.id,
                "company_id": cls.company_data["company"].id,
                "date_start": date_start,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": cls.product_a.id,
                            "quantity": 2,
                            "price_unit": 100.0,
                        }
                    )
                ],
                **vals,
            }
        )
        contract.action_start()
        return contract
