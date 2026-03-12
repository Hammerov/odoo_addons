from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    use_manual_currency_rate = fields.Boolean(
        string="Use Manual Currency Rate"
    )

    manual_currency_rate = fields.Float(
        string="Manual Currency Rate",
        digits=(12, 6)
    )