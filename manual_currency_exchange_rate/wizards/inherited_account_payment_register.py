# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Sitaram Solutions (<https://sitaramsolutions.in/>).
#
#    For Module Support : info@sitaramsolutions.in  or Skype : contact.hiren1188
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class srAccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate')
    main_currency_exchange_rate = fields.Float(string='Main Currency Exchange Rate')
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)

    
    @api.onchange('main_currency_exchange_rate')
    def onchange_main_currency_exchange_rate(self):
        for order in self:
            order.manual_currency_exchange_rate = 0
            if order.main_currency_exchange_rate:
                order.manual_currency_exchange_rate = 1.00 / order.main_currency_exchange_rate
                

    # New Code
    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

        if not self.can_edit_wizard or not self.currency_id or not self.payment_date or not self.custom_user_amount:
            return

        if self.custom_user_amount:
            self.custom_user_amount = self.amount = self.custom_user_currency_id._convert(
                from_amount=self.custom_user_amount,
                to_currency=self.currency_id,
                date=self.payment_date,
                company=self.company_id,
            )
            
    @api.model
    def default_get(self, fields):
        result = super(srAccountPaymentRegister, self).default_get(fields)
        move_id = self.env['account.move.line'].browse(self._context.get('active_ids')).filtered(lambda move: move.move_id.is_invoice(include_receipts=True))
        if len(move_id.move_id) !=1:
            return result
        else:
            result.update({
                'apply_manual_currency_exchange': move_id.move_id.apply_manual_currency_exchange,
                'manual_currency_exchange_rate': move_id.move_id.manual_currency_exchange_rate,
                'main_currency_exchange_rate': move_id.move_id.main_currency_exchange_rate,
            })
            return result

    # New code
    @api.depends('can_edit_wizard', 'source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id', 'payment_date', 'installments_mode')
    def _compute_amount(self):
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id or not wizard.payment_date or wizard.custom_user_amount:
                wizard.amount = wizard.amount
            else:
                total_amount_values = wizard._get_total_amounts_to_pay(wizard.batches)
                wizard.amount = total_amount_values['amount_by_default']

    # New Code
    @api.depends('can_edit_wizard', 'amount', 'installments_mode')
    def _compute_payment_difference(self):
        for wizard in self:
            if wizard.payment_date:
                total_amount_values = wizard._get_total_amounts_to_pay(wizard.batches)
                if wizard.installments_mode in ('overdue', 'next', 'before_date'):
                    wizard.payment_difference = total_amount_values['amount_for_difference'] - wizard.amount
                elif wizard.installments_mode == 'full':
                    wizard.payment_difference = total_amount_values['full_amount_for_difference'] - wizard.amount
                else:
                    if wizard.apply_manual_currency_exchange:
                        amount_payment_currency = wizard.company_id.currency_id.with_context(
                            manual_rate=wizard.manual_currency_exchange_rate,
                            active_manutal_currency = wizard.apply_manual_currency_exchange,
                        )._convert(wizard.source_amount, wizard.currency_id, wizard.company_id, wizard.payment_date)
                        wizard.payment_difference = amount_payment_currency - wizard.amount
                    else:
                        wizard.payment_difference = total_amount_values['amount_for_difference'] - wizard.amount
            else:
                wizard.payment_difference = 0.0

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'memo': self.communication,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'destination_account_id': self.line_ids[0].account_id.id,
            'write_off_line_vals': [],
            'apply_manual_currency_exchange':self.apply_manual_currency_exchange,
            'manual_currency_exchange_rate':self.manual_currency_exchange_rate,
            'main_currency_exchange_rate':self.main_currency_exchange_rate,
            'active_manual_currency_rate':self.active_manual_currency_rate
        }

        if self.payment_difference_handling == 'reconcile':
            if self.early_payment_discount_mode:
                epd_aml_values_list = []
                for aml in batch_result['lines']:
                    if aml.move_id._is_eligible_for_early_payment_discount(self.currency_id, self.payment_date):
                        epd_aml_values_list.append({
                            'aml': aml,
                            'amount_currency': -aml.amount_residual_currency,
                            'balance': aml.currency_id._convert(-aml.amount_residual_currency, aml.company_currency_id, date=self.payment_date),
                        })

                open_amount_currency = self.payment_difference * (-1 if self.payment_type == 'outbound' else 1)
                open_balance = self.currency_id._convert(open_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date)
                early_payment_values = self.env['account.move']._get_invoice_counterpart_amls_for_early_payment_discount(epd_aml_values_list, open_balance)
                for aml_values_list in early_payment_values.values():
                    payment_vals['write_off_line_vals'] += aml_values_list

            elif not self.currency_id.is_zero(self.payment_difference):

                if self.writeoff_is_exchange_account:
                    if self.currency_id != self.company_currency_id:
                        payment_vals['force_balance'] = sum(batch_result['lines'].mapped('amount_residual'))
                else:
                    if self.payment_type == 'inbound':
                        write_off_amount_currency = self.payment_difference
                    else:
                        write_off_amount_currency = -self.payment_difference

                    payment_vals['write_off_line_vals'].append({
                        'name': self.writeoff_label,
                        'account_id': self.writeoff_account_id.id,
                        'partner_id': self.partner_id.id,
                        'currency_id': self.currency_id.id,
                        'amount_currency': write_off_amount_currency,
                        'balance': self.currency_id._convert(write_off_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date),
                    })
        return payment_vals
