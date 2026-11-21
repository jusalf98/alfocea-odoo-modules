{
    "name": "Subscription Portal",
    "summary": "Customers see, download, pause and cancel their subscriptions",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "website": "https://github.com/jusalf98/alfocea-odoo-modules",
    "author": "Justo Alfocea Frutos",
    "license": "LGPL-3",
    "depends": ["alfo_subscription_core", "portal"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/subscription_plan_views.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
}
