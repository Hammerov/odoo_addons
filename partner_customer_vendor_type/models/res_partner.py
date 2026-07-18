from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean(
        string='Customer',
        help='Check this box if this contact is a customer. '
             'Customer contacts are the only ones shown in the '
             '"Customer" field on Customer Invoices.',
    )
    is_vendor = fields.Boolean(
        string='Vendor',
        help='Check this box if this contact is a vendor/supplier. '
             'Vendor contacts are the only ones shown in the '
             '"Vendor" field on Vendor Bills.',
    )
