from odoo.tests import tagged

from .common import AlfoSubscriptionAccountCommon


@tagged("post_install", "-at_install")
class TestRenewalDocumentIntegration(AlfoSubscriptionAccountCommon):
    """With the sale, purchase and account integrations installed together, every
    subscription is renewed with exactly one kind of document: never twice."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Module = cls.env["ir.module.module"].sudo()
        installed = Module.search(
            [
                (
                    "name",
                    "in",
                    ("alfo_subscription_sale", "alfo_subscription_purchase"),
                ),
                ("state", "=", "installed"),
            ]
        )
        cls.full_suite = len(installed) == 2

    def setUp(self):
        super().setUp()
        if not self.full_suite:
            self.skipTest("Needs alfo_subscription_sale and alfo_subscription_purchase")

    def _run_all_renewal_crons(self):
        # Scheduled actions run as superuser, as in production.
        Contract = self.SubscriptionContract.sudo()
        Contract._cron_create_recurring_sale_orders()
        Contract._cron_create_recurring_purchase_orders()
        Contract._cron_create_recurring_invoices()

    def test_each_subscription_is_renewed_once(self):
        by_order = self._create_running_contract(
            self.today, renewal_document="sale_order"
        )
        by_purchase = self._create_running_contract(
            self.today, contract_type="purchase", renewal_document="purchase_order"
        )
        by_invoice = self._create_running_contract(self.today)

        self._run_all_renewal_crons()

        self.assertEqual(len(by_order.sale_order_ids), 1)
        self.assertFalse(by_order.invoice_ids)
        self.assertEqual(len(by_purchase.purchase_order_ids), 1)
        self.assertFalse(by_purchase.invoice_ids)
        self.assertEqual(len(by_invoice.invoice_ids), 1)
        self.assertFalse(by_invoice.sale_order_ids)
