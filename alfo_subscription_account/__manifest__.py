{
    "name": "Subscription Account",
    "summary": "Invoice subscriptions directly: customer invoices and vendor bills",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "website": "https://github.com/jusalf98/alfocea-odoo-modules",
    "author": "Justo Alfocea Frutos",
    "license": "LGPL-3",
    "depends": ["alfo_subscription_core", "account"],
    "data": [
        "data/ir_cron_data.xml",
        "views/account_move_views.xml",
        "views/subscription_contract_views.xml",
        "views/subscription_plan_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
