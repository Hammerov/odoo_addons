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
from contextlib import contextmanager


class AccountMove(models.Model):
    _inherit = 'account.move'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    main_currency_exchange_rate = fields.Float(string='Main Currency Exchange Rate')
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate')
    active_manual_currency_rate = fields.Boolean('active Manual Currency')


    @api.onchange('main_currency_exchange_rate')
    def onchange_main_currency_exchange_rate(self):
        for order in self:
            order.manual_currency_exchange_rate = 0
            if order.main_currency_exchange_rate:
                order.manual_currency_exchange_rate = 1.00 / order.main_currency_exchange_rate


    @api.onchange('company_id', 'currency_id')
    def onchange_currency_id(self):
        if self.company_id or self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date', 'apply_manual_currency_exchange', 'manual_currency_exchange_rate')
    def _compute_invoice_currency_rate(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                if move.currency_id:
                    if move.apply_manual_currency_exchange:
                        move.invoice_currency_rate = move.manual_currency_exchange_rate
                    else:
                        move.invoice_currency_rate = self.env['res.currency']._get_conversion_rate(
                            from_currency=move.company_currency_id,
                            to_currency=move.currency_id,
                            company=move.company_id,
                            date=move.invoice_date or fields.Date.context_today(move),
                        )
                else:
                    move.invoice_currency_rate = 1
    
    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.origin_payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'state',
        'apply_manual_currency_exchange',
        'manual_currency_exchange_rate',
        'active_manual_currency_rate')
    def _compute_amount(self):
        return super()._compute_amount()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # New changes
    @api.depends('currency_id', 'company_id', 'move_id.invoice_currency_rate', 'move_id.date', 'move_id.apply_manual_currency_exchange', 'move_id.manual_currency_exchange_rate')
    def _compute_currency_rate(self):
        for line in self:
            if line.move_id.apply_manual_currency_exchange:
                line.currency_rate = line.move_id.manual_currency_exchange_rate
            elif line.move_id.is_invoice(include_receipts=True):
                line.currency_rate = line.move_id.invoice_currency_rate
            elif line.currency_id:
                if line.move_id.apply_manual_currency_exchange:
                    line.currency_rate = line.move_id.manual_currency_exchange_rate
                else:
                    line.currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=line.company_currency_id,
                        to_currency=line.currency_id,
                        company=line.company_id,
                        date=line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line),
                    )
            else:
                line.currency_rate = 1

#     @api.depends('product_id', 'product_uom_id', 'move_id.apply_manual_currency_exchange', 'move_id.manual_currency_exchange_rate')
#     def _compute_price_unit(self):
#         for line in self:
#             if not line.product_id or line.display_type in ('line_section', 'line_note') or line.is_imported:
#                 continue
#             if line.move_id.is_sale_document(include_receipts=True):
#                 document_type = 'sale'
#             elif line.move_id.is_purchase_document(include_receipts=True):
#                 document_type = 'purchase'
#             else:
#                 document_type = 'other'
#             if line.move_id.apply_manual_currency_exchange:
#                 line.price_unit = line.product_id.lst_price * line.move_id.manual_currency_exchange_rate
#             else:
#                 line.price_unit = line.product_id._get_tax_included_unit_price(
#                     line.move_id.company_id,
#                     line.move_id.currency_id,
#                     line.move_id.date,
#                     document_type,
#                     fiscal_position=line.move_id.fiscal_position_id,
#                     product_uom=line.product_uom_id,
#                 )

    @contextmanager
    def _sync_invoice(self, container):
        if container['records'].env.context.get('skip_invoice_line_sync'):
            yield
            return  # avoid infinite recursion

        def existing():
            return {
                line: {
                    'amount_currency': line.currency_id.round(line.amount_currency),
                    'balance': line.company_id.currency_id.round(line.balance),
                    'currency_rate': line.currency_rate,
                    'price_subtotal': line.currency_id.round(line.price_subtotal),
                    'move_type': line.move_id.move_type,
                } for line in container['records'].with_context(
                    skip_invoice_line_sync=True,
                ).filtered(lambda l: l.move_id.is_invoice(True))
            }

        def changed(fname):
            return line not in before or before[line][fname] != after[line][fname]

        before = existing()
        yield
        after = existing()
        protected = container.get('protected', {})
        for line in after:
            if (
                (changed('amount_currency') or changed('currency_rate') or changed('move_type'))
                and 'balance' not in protected.get(line, {})
                and (not changed('balance') or (line not in before and not line.balance))
            ):
                if line.amount_currency and line.currency_rate:
                    balance = line.company_id.currency_id.round(line.amount_currency / line.currency_rate)
                else:
                    balance = 0
                line.balance = balance

        self.env.add_to_compute(self._fields['debit'], container['records'])
        self.env.add_to_compute(self._fields['credit'], container['records'])



    # Fully override to pass manual currency rate in residual amount
    @api.model
    def _prepare_move_line_residual_amounts(self, aml_values, counterpart_currency, shadowed_aml_values=None, other_aml_values=None):
        """ Prepare the available residual amounts for each currency.
        :param aml_values: The values of account.move.line to consider.
        :param counterpart_currency: The currency of the opposite line this line will be reconciled with.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :param other_aml_values:    The other aml values to be reconciled with the current one.
        :return: A mapping currency -> dictionary containing:
            * residual: The residual amount left for this currency.
            * rate:     The rate applied regarding the company's currency.
        """

        def is_payment(aml):
            return aml.move_id.origin_payment_id or aml.move_id.statement_line_id

        def get_odoo_rate(aml, other_aml, currency):
            if forced_rate := self._context.get('forced_rate_from_register_payment'):
                return forced_rate
            if other_aml and not is_payment(aml) and is_payment(other_aml):
                return get_accounting_rate(other_aml, currency)
            if aml.move_id.is_invoice(include_receipts=True):
                exchange_rate_date = aml.move_id.invoice_date
            else:
                exchange_rate_date = aml._get_reconciliation_aml_field_value('date', shadowed_aml_values)
                
            if aml.payment_id.apply_manual_currency_exchange: #Patch
                return aml.payment_id.manual_currency_exchange_rate #Patch
                
            return currency._get_conversion_rate(aml.company_currency_id, currency, aml.company_id, exchange_rate_date)

        def get_accounting_rate(aml, currency):
            if forced_rate := self._context.get('forced_rate_from_register_payment'):
                return forced_rate
            balance = aml._get_reconciliation_aml_field_value('balance', shadowed_aml_values)
            amount_currency = aml._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values)
            if not aml.company_currency_id.is_zero(balance) and not currency.is_zero(amount_currency):
                return abs(amount_currency / balance)

        aml = aml_values['aml']
        other_aml = (other_aml_values or {}).get('aml')
        remaining_amount_curr = aml_values['amount_residual_currency']
        remaining_amount = aml_values['amount_residual']
        company_currency = aml.company_currency_id
        currency = aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        account = aml._get_reconciliation_aml_field_value('account_id', shadowed_aml_values)
        has_zero_residual = company_currency.is_zero(remaining_amount)
        has_zero_residual_currency = currency.is_zero(remaining_amount_curr)
        is_rec_pay_account = account.account_type in ('asset_receivable', 'liability_payable')

        available_residual_per_currency = {}

        if not has_zero_residual:
            available_residual_per_currency[company_currency] = {
                'residual': remaining_amount,
                'rate': 1,
            }
        if currency != company_currency and not has_zero_residual_currency:
            available_residual_per_currency[currency] = {
                'residual': remaining_amount_curr,
                'rate': get_accounting_rate(aml, currency),
            }

        if currency == company_currency \
            and is_rec_pay_account \
            and not has_zero_residual \
            and counterpart_currency != company_currency:
            rate = get_odoo_rate(aml, other_aml, counterpart_currency)
            residual_in_foreign_curr = counterpart_currency.round(remaining_amount * rate)
            if not counterpart_currency.is_zero(residual_in_foreign_curr):
                available_residual_per_currency[counterpart_currency] = {
                    'residual': residual_in_foreign_curr,
                    'rate': rate,
                }
        elif currency == counterpart_currency \
            and currency != company_currency \
            and not has_zero_residual_currency:
            available_residual_per_currency[counterpart_currency] = {
                'residual': remaining_amount_curr,
                'rate': get_accounting_rate(aml, currency),
            }
        return available_residual_per_currency



