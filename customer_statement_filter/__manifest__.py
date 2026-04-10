{
    'name': 'Customer Statement Filter (QB Style)',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'QuickBooks style customer statement wizard',
    'depends': ['account', 'account_followup'], # account_followup is required for the report engine
    'data': [
        'security/ir.model.access.csv',
        'views/statement_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
