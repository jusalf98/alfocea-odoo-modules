from odoo import Command, api, fields, models

INVOICE_TYPES = {"sale": "out_invoice", "purchase": "in_invoice"}


class SubscriptionContract(models.Model):
    _inherit = "subscription.contract"

    renewal_document = fields.Selection(
        selection_add=[("invoice", "Invoice")],
        ondelete={"invoice": lambda recs: recs.write({"renewal_document": "none"})},
    )
    invoice_ids = fields.One2many(
        "account.move", "subscription_contract_id", string="Invoices", readonly=True
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for contract in self:
            contract.invoice_count = len(contract.invoice_ids)

    def _get_default_renewal_document(self):
        # Orders (sale / purchase modules) are preferred when they are installed:
        # invoices are only the default when no other document applies.
        document = super()._get_default_renewal_document()
        return "invoice" if document == "none" else document

    def action_view_invoices(self):
        self.ensure_one()
        xml_id = (
            "account.action_move_out_invoice_type"
            if self.contract_type == "sale"
            else "account.action_move_in_invoice_type"
        )
        action = self.env["ir.actions.act_window"]._for_xml_id(xml_id)
        invoices = self.invoice_ids
        if len(invoices) == 1:
            action.update(
                {"views": [(False, "form")], "view_mode": "form", "res_id": invoices.id}
            )
        else:
            action["domain"] = [("id", "in", invoices.ids)]
        return action

    @api.model
    def _cron_create_recurring_invoices(self):
        """Create the invoices and vendor bills of the subscriptions that are due."""
        self._process_renewals("invoice", "_create_recurring_invoices")

    def _create_recurring_invoices(self, date):
        """Create one invoice (or vendor bill) per due period up to ``date``."""
        self.ensure_one()
        periods, next_invoice_date = self._get_due_periods(date)
        Move = self.env["account.move"].with_company(self.company_id)
        if not periods:
            return Move
        invoices = Move.create(
            [self._prepare_renewal_invoice_vals(*period) for period in periods]
        )
        self.next_invoice_date = next_invoice_date
        if self.plan_id.invoice_auto_post:
            invoices.action_post()
        return invoices

    def _prepare_renewal_invoice_vals(self, period_start, period_end):
        self.ensure_one()
        period = self._get_period_description(period_start, period_end)
        return {
            "move_type": INVOICE_TYPES[self.contract_type],
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "invoice_date": period_start,
            "invoice_origin": self.name,
            "subscription_contract_id": self.id,
            "invoice_line_ids": [
                Command.create(line._prepare_renewal_invoice_line_vals(period))
                for line in self.line_ids
            ],
        }
