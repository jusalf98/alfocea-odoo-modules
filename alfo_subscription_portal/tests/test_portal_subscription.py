from odoo import Command, fields, http
from odoo.tests import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPortalSubscription(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(
            cls.env,
            login="sub_portal",
            password="sub_portal",
            groups="base.group_portal",
        )
        cls.customer = cls.portal_user.partner_id
        cls.other_customer = cls.env["res.partner"].create({"name": "Other Customer"})
        cls.plan = cls.env["subscription.plan"].create(
            {"name": "Portal Monthly", "periodicity": "monthly"}
        )
        product = cls.env["product.product"].create(
            {"name": "Portal Box", "list_price": 20.0}
        )
        today = fields.Date.today()
        Contract = cls.env["subscription.contract"]
        cls.contract, cls.other_contract = Contract.create(
            [
                {
                    "partner_id": partner.id,
                    "plan_id": cls.plan.id,
                    "date_start": today,
                    "line_ids": [Command.create({"product_id": product.id})],
                }
                for partner in (cls.customer, cls.other_customer)
            ]
        )
        (cls.contract | cls.other_contract).action_start()

    def _post(self, contract, action, **data):
        return self.url_open(
            f"/my/subscriptions/{contract.id}/{action}",
            data={"csrf_token": http.Request.csrf_token(self), **data},
        )

    def test_customer_sees_only_their_subscriptions(self):
        self.authenticate("sub_portal", "sub_portal")
        response = self.url_open("/my/subscriptions")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.contract.name, response.text)
        self.assertNotIn(self.other_contract.name, response.text)

        response = self.url_open(self.contract.get_portal_url())
        self.assertIn(self.contract.name, response.text)
        self.assertIn("Every month", response.text)

        # Without the share link (access token), another customer's subscription
        # is not accessible.
        response = self.url_open(f"/my/subscriptions/{self.other_contract.id}")
        self.assertNotIn(self.other_contract.name, response.text)
        self.assertTrue(response.url.endswith(("/my", "/my/home")))

    def test_home_counter(self):
        self.authenticate("sub_portal", "sub_portal")
        response = self.url_open("/my/home")
        self.assertIn("/my/subscriptions", response.text)

    def test_report_from_the_portal(self):
        self.authenticate("sub_portal", "sub_portal")
        response = self.url_open(self.contract.get_portal_url(report_type="html"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.contract.name, response.text)

    def test_pause_only_when_the_plan_allows_it(self):
        self.authenticate("sub_portal", "sub_portal")
        self._post(self.contract, "pause")
        self.assertEqual(self.contract.state, "active")

        self.plan.portal_allow_pause = True
        self._post(self.contract, "pause")
        self.assertEqual(self.contract.state, "paused")
        message = self.contract.message_ids.filtered(
            lambda m: "Paused by the customer" in (m.body or "")
        )
        self.assertEqual(len(message), 1)
        self.assertEqual(message.author_id, self.customer)

        self._post(self.contract, "resume")
        self.assertEqual(self.contract.state, "active")

    def test_cancel_from_the_portal(self):
        self.plan.portal_allow_cancel = True
        reason = self.env.ref("alfo_subscription_core.close_reason_too_expensive")
        self.authenticate("sub_portal", "sub_portal")

        # The cancel dialog offers the close reasons, but not the pause one.
        response = self.url_open(self.contract.get_portal_url())
        self.assertIn('name="reason_id"', response.text)
        self.assertIn(reason.name, response.text)
        self.assertNotIn(
            self.env.ref("alfo_subscription_core.close_reason_temporary").name,
            response.text,
        )

        self._post(self.other_contract, "cancel", reason_id=reason.id)
        self.assertEqual(self.other_contract.state, "active")

        # Without a valid reason nothing is cancelled.
        response = self._post(self.contract, "cancel")
        self.assertEqual(self.contract.state, "active")
        self.assertIn("error=1", response.url)
        temporary = self.env.ref("alfo_subscription_core.close_reason_temporary")
        self._post(self.contract, "cancel", reason_id=temporary.id)
        self.assertEqual(self.contract.state, "active")

        self._post(
            self.contract, "cancel", reason_id=reason.id, comment="<b>Too much</b>"
        )
        self.assertEqual(self.contract.state, "cancelled")
        self.assertEqual(self.contract.date_closed, fields.Date.today())
        self.assertEqual(self.contract.close_reason_id, reason)
        message = self.contract.message_ids.filtered(
            lambda m: "Cancelled by the customer" in (m.body or "")
        )
        self.assertEqual(message.author_id, self.customer)
        self.assertIn(reason.name, message.body)
        # The customer's comment is escaped, not rendered as HTML.
        self.assertIn("&lt;b&gt;Too much&lt;/b&gt;", message.body)

    def test_stop_renewal_from_the_portal(self):
        self.plan.write(
            {"portal_allow_cancel": True, "auto_renew": True, "notice_days": 5}
        )
        self.contract.date_end = fields.Date.add(fields.Date.today(), months=2)
        self.authenticate("sub_portal", "sub_portal")
        self.assertFalse(self.contract._portal_can_cancel())
        self._post(self.contract, "stop_renewal")
        self.assertTrue(self.contract.do_not_renew)
        self.assertEqual(self.contract.state, "active")
