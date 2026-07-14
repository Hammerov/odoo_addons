# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Sitaram Solutions (<https://sitaramsolutions.in/>).
#
#    For Module Support : info@sitaramsolutions.in  or Skype : contact.hiren1188
#
##############################################################################

from odoo import models, fields, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    # New Code
    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company=None, date=None):
        if from_currency == to_currency:
            return 1
        if self._context.get('active_manutal_currency'):
            res = self._context.get('manual_rate')
            return res
        else:
            company = company or self.env.company
            date = date or fields.Date.context_today(self)
            return from_currency.with_company(company).with_context(to_currency=to_currency.id, date=str(date)).inverse_rate
