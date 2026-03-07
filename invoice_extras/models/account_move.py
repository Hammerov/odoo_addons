from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    delivery_note_no = fields.Char(string="Delivery Note No.")
    lpo_number = fields.Char(string="L.P.O Number")
