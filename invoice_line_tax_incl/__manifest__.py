{
    "name": "Invoice Line Tax Inclusive Column",
    "version": "1.0",
    "category": "Accounting",
    "depends": ["account"],
    "data": [
        "views/account_move_views.xml",
        "views/report_invoice_templates.xml", # Add this line
    ],
    "installable": True,
}