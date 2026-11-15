{
    "name": "Subscription Sale",
    "summary": "Create and start subscriptions automatically from sale orders",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "website": "https://github.com/jusalf98/alfocea-odoo-modules",
    "author": "Justo Alfocea Frutos",
    "license": "LGPL-3",
    "depends": ["alfo_subscription_core", "sale"],
    "data": [
        "data/ir_cron_data.xml",
        "views/sale_order_views.xml",
        "views/subscription_contract_views.xml",
        "views/subscription_plan_views.xml",
    ],
    "installable": True,
}
