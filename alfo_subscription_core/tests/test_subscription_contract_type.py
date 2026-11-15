from odoo import fields

from .common import AlfoSubscriptionCoreCommon


class TestSubscriptionContractType(AlfoSubscriptionCoreCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = fields.Date.context_today(cls.SubscriptionContract)

    def _create_purchase_contract(self, **extra_vals):
        return self._create_contract(
            self.plan_monthly,
            self.today,
            contract_type="purchase",
            partner_id=self.vendor.id,
            **extra_vals,
        )

    def test_sale_is_the_default_type(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        self.assertEqual(contract.contract_type, "sale")
        self.assertTrue(contract.name.startswith("SUB/"))
        self.assertEqual(contract.line_ids.price_unit, 25.0)

    def test_purchase_sequence(self):
        contract = self._create_purchase_contract()
        self.assertTrue(contract.name.startswith("PSUB/"))

    def test_type_from_context_default(self):
        contract = self.SubscriptionContract.with_context(
            default_contract_type="purchase"
        ).create({"partner_id": self.vendor.id, "plan_id": self.plan_monthly.id})
        self.assertEqual(contract.contract_type, "purchase")
        self.assertTrue(contract.name.startswith("PSUB/"))

    def test_purchase_price_from_product_cost(self):
        contract = self._create_purchase_contract()
        self.assertEqual(contract.line_ids.price_unit, 15.0)
        self.assertEqual(contract.amount_total, 15.0)

    def test_purchase_price_from_vendor_pricelist(self):
        self.env["product.supplierinfo"].create(
            {
                "partner_id": self.vendor.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "price": 12.0,
            }
        )
        contract = self._create_purchase_contract()
        self.assertEqual(contract.line_ids.price_unit, 12.0)

    def test_other_vendor_pricelist_is_ignored(self):
        self.env["product.supplierinfo"].create(
            {
                "partner_id": self.partner.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "price": 9.0,
            }
        )
        contract = self._create_purchase_contract()
        self.assertEqual(contract.line_ids.price_unit, 15.0)

    def test_changing_type_recomputes_line_price(self):
        contract = self._create_contract(self.plan_monthly, self.today)
        contract.write({"contract_type": "purchase", "partner_id": self.vendor.id})
        self.assertEqual(contract.line_ids.price_unit, 15.0)

    def test_purchase_contract_flow(self):
        contract = self._create_purchase_contract()
        contract.action_start()
        self.assertEqual(contract.state, "active")
        self.assertEqual(contract.next_invoice_date, self.today)
