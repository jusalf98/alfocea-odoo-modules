from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class SubscriptionPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "subscription_count" in counters:
            Contract = request.env["subscription.contract"]
            values["subscription_count"] = (
                Contract.search_count(self._get_subscription_domain())
                if Contract.has_access("read")
                else 0
            )
        return values

    def _get_subscription_domain(self):
        # The record rules of the portal group keep the customer's ones only.
        return [("contract_type", "=", "sale"), ("state", "!=", "draft")]

    def _get_portal_close_reasons(self):
        """Close reasons a customer can choose when cancelling: all the active
        ones but the temporary break, which is a pause reason."""
        reasons = request.env["subscription.close.reason"].sudo().search([])
        pause_reason = request.env.ref(
            "alfo_subscription_core.close_reason_temporary", raise_if_not_found=False
        )
        return reasons - pause_reason if pause_reason else reasons

    @http.route(
        ["/my/subscriptions", "/my/subscriptions/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_subscriptions(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        Contract = request.env["subscription.contract"]
        domain = self._get_subscription_domain()
        pager = portal_pager(
            url="/my/subscriptions",
            total=Contract.search_count(domain),
            page=page,
            step=self._items_per_page,
        )
        values.update(
            {
                "subscriptions": Contract.search(
                    domain,
                    order="date_start desc, id desc",
                    limit=self._items_per_page,
                    offset=pager["offset"],
                ),
                "page_name": "subscription",
                "pager": pager,
                "default_url": "/my/subscriptions",
            }
        )
        return request.render(
            "alfo_subscription_portal.portal_my_subscriptions", values
        )

    @http.route(
        ["/my/subscriptions/<int:contract_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def portal_my_subscription(
        self, contract_id, access_token=None, report_type=None, download=False, **kw
    ):
        try:
            contract_sudo = self._document_check_access(
                "subscription.contract", contract_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        if report_type in ("html", "pdf", "text"):
            return self._show_report(
                model=contract_sudo,
                report_type=report_type,
                report_ref="alfo_subscription_core.action_report_subscription_contract",
                download=download,
            )
        values = self._get_page_view_values(
            contract_sudo,
            access_token,
            {
                "subscription": contract_sudo,
                "page_name": "subscription",
                "message": kw.get("message"),
                "error": kw.get("error"),
                "close_reasons": self._get_portal_close_reasons(),
            },
            "my_subscriptions_history",
            False,
        )
        return request.render("alfo_subscription_portal.portal_my_subscription", values)

    def _subscription_portal_action(self, contract_id, access_token, check, apply):
        """Check the access and the permission, apply, and log it as the customer.

        ``apply`` returns the message to log, or nothing when the request is not
        valid (e.g. a missing reason): then nothing is done and an error shown.
        """
        try:
            contract_sudo = self._document_check_access(
                "subscription.contract", contract_id, access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")
        if not getattr(contract_sudo, check)():
            return request.redirect(contract_sudo.get_portal_url())
        message = apply(contract_sudo)
        if not message:
            return request.redirect(
                contract_sudo.get_portal_url(query_string="&error=1")
            )
        contract_sudo.message_post(
            body=message, author_id=request.env.user.partner_id.id
        )
        return request.redirect(contract_sudo.get_portal_url(query_string="&message=1"))

    @http.route(
        ["/my/subscriptions/<int:contract_id>/pause"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def portal_subscription_pause(self, contract_id, access_token=None, **kw):
        def apply(contract):
            contract.action_pause()
            return request.env._("Paused by the customer from the portal.")

        return self._subscription_portal_action(
            contract_id, access_token, "_portal_can_pause", apply
        )

    @http.route(
        ["/my/subscriptions/<int:contract_id>/resume"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def portal_subscription_resume(self, contract_id, access_token=None, **kw):
        def apply(contract):
            contract.action_resume()
            return request.env._("Resumed by the customer from the portal.")

        return self._subscription_portal_action(
            contract_id, access_token, "_portal_can_resume", apply
        )

    @http.route(
        ["/my/subscriptions/<int:contract_id>/cancel"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def portal_subscription_cancel(
        self, contract_id, access_token=None, reason_id=None, comment=None, **kw
    ):
        reason = self._get_portal_close_reasons().filtered(
            lambda r: str(r.id) == str(reason_id)
        )
        comment = (comment or "").strip()[:1000]

        def apply(contract):
            if not reason:
                return False
            contract.action_cancel()
            contract.close_reason_id = reason
            # A plain string: message_post escapes the customer's comment.
            return request.env._(
                "Cancelled by the customer from the portal. Reason: %(reason)s. "
                "%(comment)s",
                reason=reason.name,
                comment=comment,
            )

        return self._subscription_portal_action(
            contract_id, access_token, "_portal_can_cancel", apply
        )

    @http.route(
        ["/my/subscriptions/<int:contract_id>/stop_renewal"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def portal_subscription_stop_renewal(self, contract_id, access_token=None, **kw):
        def apply(contract):
            contract.action_do_not_renew()
            return request.env._(
                "The customer asked from the portal not to renew the subscription."
            )

        return self._subscription_portal_action(
            contract_id, access_token, "_portal_can_stop_renewal", apply
        )
