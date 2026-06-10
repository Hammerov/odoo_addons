{
    "name": "sale_order_packs",
    "version": "1.0",
    "author":  "Salwa",
    "Maintainer": "Innovus",
    "summary": "Adding packs column to the sale order line",
    "category": "Sales",
    "depends": ["sale", "account", 'sale_stock'],
    "data": [
        "views/packs.xml",
        "views/account_move_views.xml",
        "views/delivery_slip_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
