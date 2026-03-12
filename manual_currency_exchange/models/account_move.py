from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    use_manual_currency_rate = fields.Boolean(
        string="Use Manual Currency Rate"
    )

    manual_currency_rate = fields.Float(
        string="Manual Currency Rate",
        digits=(12, 6)
    )

    @api.constrains('manual_currency_rate')
    def _check_manual_rate(self):
        for move in self:
            if move.use_manual_currency_rate and move.manual_currency_rate <= 0:
                raise ValidationError("Manual currency rate must be greater than zero.")

    def _get_currency_rate(self):
        """Return manual rate if enabled"""
        self.ensure_one()

        if self.use_manual_currency_rate and self.manual_currency_rate:
            return self.manual_currency_rate

        return super()._get_currency_rate()

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        """Ensure totals recompute when manual rate changes"""
        res = super()._recompute_dynamic_lines(
            recompute_all_taxes=recompute_all_taxes,
            recompute_tax_base_amount=recompute_tax_base_amount
        )
        return res