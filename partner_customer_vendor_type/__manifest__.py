{
    'name': 'Partner Customer / Vendor Type',
    'version': '19.0.1.0.0',
    'category': 'Contacts',
    'summary': 'Flag contacts as Customer/Vendor and filter partner dropdowns on invoices & bills',
    'description': """
Partner Customer / Vendor Type
===============================

Adds two checkboxes on the Contact form:

* **Customer**
* **Vendor**

These flags are then used to filter the *Customer* field on Customer
Invoices and the *Vendor* field on Vendor Bills, so each dropdown only
shows relevant contacts. Also adds "Customers" / "Vendors" quick
filters on the Contacts search view.

When a new contact is quick-created directly from a Vendor Bill or a
Customer Invoice, the corresponding checkbox is ticked automatically.
""",
    'author': 'Hammerov',
    'license': 'LGPL-3',
    'depends': ['contacts', 'account'],
    'data': [
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
