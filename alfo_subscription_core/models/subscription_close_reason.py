from odoo import fields, models


class SubscriptionCloseReason(models.Model):
    """Why a subscription is cancelled or paused (churn analysis)."""

    _name = "subscription.close.reason"
    _description = "Subscription Close Reason"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
