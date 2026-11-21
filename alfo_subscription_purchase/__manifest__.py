{
    "name": "Subscription Purchase",
    "summary": "Vendor subscriptions from purchase orders and renewal purchase orders",
    "version": "18.0.1.4.0",
    "category": "Purchases",
    "website": "https://github.com/jusalf98/alfocea-odoo-modules",
    "author": "Justo Alfocea Frutos",
    "license": "LGPL-3",
    "depends": ["alfo_subscription_core", "purchase"],
    "data": [
        "data/ir_cron_data.xml",
        "views/product_template_views.xml",
        "views/purchase_order_views.xml",
        "views/subscription_contract_views.xml",
        "views/subscription_plan_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
}
