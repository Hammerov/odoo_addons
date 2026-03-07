from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    packs = fields.Char(string="Packs")