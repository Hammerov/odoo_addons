# -*- coding: utf-8 -*-
{
    'name': 'Partner Statement Report',
    'description': """
            Partner Statement Report
    """,
    'summary': 'Partner Statement Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'author': 'Yunus Abdulaziz',
    'website': "yuab.odoo@gmail.com",
    'depends': [
        'contacts',
        'account',
        'mail',
    ],
    'data': [
        # Security
        'security/security_access.xml',
        'security/ir.model.access.csv',
        # Data
        'data/mail_template.xml',
        # Wizard
        'wizard/partner_statement_view.xml',
        # Report
        'report/partner_statement_report_pdf.xml',
        # Views
        'views/menus.xml',
    ],
    'images': ['static/description/images/main_screenshot.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
