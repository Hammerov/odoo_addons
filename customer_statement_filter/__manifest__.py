{
    'name': 'Customer Statement Filter (QB Style)',
    'version': '1.1',
    'category': 'Accounting',
    'summary': 'QuickBooks style customer statement wizard with running balance',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account', 
        'account_followup'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/statement_wizard_views.xml',
        'views/report_partner_statement.xml', # This links your new PDF design
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}