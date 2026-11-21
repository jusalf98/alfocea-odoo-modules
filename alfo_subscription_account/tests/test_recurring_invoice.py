from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from .common import AlfoSubscriptionAccountCommon


@tagged("post_install", "-at_install")
class TestRecurringInvoice(AlfoSubscriptionAccountCommon):
    def _run_cron(self):
        self.SubscriptionContract._cron_create_recurring_invoices()

    def test_invoice_is_the_default_renewal_document(self):
        customer, vendor = self.SubscriptionContract.create(
            [
                {"partner_id": self.partner_a.id, "plan_id": self.plan_monthly.id},
                {
                    "contract_type": "purchase",
                    "partner_id": self.partner_a.id,
                    "plan_id": self.plan_monthly.id,
                },
            ]
        )
        # Invoices are the default unless the sale / purchase integration modules
        # are installed: then orders are preferred.
        documents = dict(
            self.SubscriptionContract._fields["renewal_document"].selection
        )
        self.assertEqual(
            customer.renewal_document,
            "sale_order" if "sale_order" in documents else "invoice",
        )
        self.assertEqual(
            vendor.renewal_document,
            "purchase_order" if "purchase_order" in documents else "invoice",
        )

    def test_reset_renewal_document(self):
        """Used by the install hooks and migrations: back to the default document."""
        contract = self._create_running_contract(self.today)
        default = contract._get_default_renewal_document()
        contract.renewal_document = "none"
        contract._reset_renewal_document()
        self.assertEqual(contract.renewal_document, default)

    def test_customer_subscription_creates_draft_invoice(self):
        contract = self._create_running_contract(self.today)
        self._run_cron()

        invoice = contract.invoice_ids
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, "out_invoice")
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.partner_id, self.partner_a)
        self.assertEqual(invoice.invoice_date, self.today)
        self.assertEqual(invoice.invoice_origin, contract.name)
        self.assertEqual(invoice.invoice_line_ids.product_id, self.product_a)
        self.assertEqual(invoice.invoice_line_ids.quantity, 2)
        # Contract price, not the product sales price (1000)
        self.assertEqual(invoice.invoice_line_ids.price_unit, 100.0)
        self.assertIn("Period:", invoice.invoice_line_ids.name)
        self.assertEqual(
            contract.next_invoice_date, self.today + relativedelta(months=1)
        )

    def test_vendor_subscription_creates_vendor_bill(self):
        contract = self._create_running_contract(self.today, contract_type="purchase")
        self._run_cron()
        self.assertEqual(contract.invoice_ids.move_type, "in_invoice")

    def test_auto_post(self):
        self.plan_monthly.invoice_auto_post = True
        contract = self._create_running_contract(self.today)
        self._run_cron()
        self.assertEqual(contract.invoice_ids.state, "posted")

    def test_missed_periods_are_caught_up(self):
        contract = self._create_running_contract(self.today - relativedelta(months=2))
        self._run_cron()
        self.assertEqual(len(contract.invoice_ids), 3)
        self.assertEqual(
            sorted(contract.invoice_ids.mapped("invoice_date")),
            [
                self.today - relativedelta(months=2),
                self.today - relativedelta(months=1),
                self.today,
            ],
        )

    def test_cron_is_idempotent(self):
        contract = self._create_running_contract(self.today)
        self._run_cron()
        self._run_cron()
        self.assertEqual(len(contract.invoice_ids), 1)

    def test_not_due_paused_and_other_documents_are_ignored(self):
        future = self._create_running_contract(self.today)
        future.next_invoice_date = self.today + relativedelta(days=1)
        paused = self._create_running_contract(self.today)
        paused.action_pause()
        no_document = self._create_running_contract(self.today)
        no_document.renewal_document = "none"
        self._run_cron()
        self.assertFalse(future.invoice_ids)
        self.assertFalse(paused.invoice_ids)
        self.assertFalse(no_document.invoice_ids)

    def test_smart_buttons(self):
        contract = self._create_running_contract(self.today)
        self._run_cron()
        invoice = contract.invoice_ids
        self.assertEqual(contract.action_view_invoices()["res_id"], invoice.id)
        self.assertEqual(
            invoice.action_view_subscription_contract()["res_id"], contract.id
        )
