# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, api


class InvoiceAbstractReport(models.AbstractModel):
    """
    Abstract model for generating customer invoice reports,
    including invoice details, payments, and balances.
    """
    _name = 'report.partner_statement_report.customer_report_template'
    _description = 'Invoice Report'

    def _get_aging_buckets(self, partner, aging_type='days', as_of_date=None, move_type='out_invoice'):
        as_of = as_of_date or date.today()
        buckets = {'current': 0.0, 'b_1_30': 0.0, 'b_30_60': 0.0,
                   'b_60_90': 0.0, 'b_90_120': 0.0, 'b_over_120': 0.0}
        open_invoices = self.env['account.move'].search([
            ('partner_id', '=', partner.id),
            ('move_type', '=', move_type),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
            ('invoice_date', '<=', as_of),
        ])
        if aging_type == 'months':
            m0 = as_of.replace(day=1)
            m1 = m0 - relativedelta(months=1)
            m2 = m0 - relativedelta(months=2)
            m3 = m0 - relativedelta(months=3)
            m4 = m0 - relativedelta(months=4)
            for inv in open_invoices:
                balance = inv.amount_residual
                if balance <= 0:
                    continue
                due = inv.invoice_date_due or inv.invoice_date or as_of
                if due >= m0:
                    buckets['current'] += balance
                elif due >= m1:
                    buckets['b_1_30'] += balance
                elif due >= m2:
                    buckets['b_30_60'] += balance
                elif due >= m3:
                    buckets['b_60_90'] += balance
                elif due >= m4:
                    buckets['b_90_120'] += balance
                else:
                    buckets['b_over_120'] += balance
        else:
            for inv in open_invoices:
                balance = inv.amount_residual
                if balance <= 0:
                    continue
                due = inv.invoice_date_due or inv.invoice_date or as_of
                days_overdue = (as_of - due).days
                if days_overdue <= 0:
                    buckets['current'] += balance
                elif days_overdue <= 30:
                    buckets['b_1_30'] += balance
                elif days_overdue <= 60:
                    buckets['b_30_60'] += balance
                elif days_overdue <= 90:
                    buckets['b_60_90'] += balance
                elif days_overdue <= 120:
                    buckets['b_90_120'] += balance
                else:
                    buckets['b_over_120'] += balance
        buckets['total'] = sum(buckets.values())
        return {k: round(v, 2) for k, v in buckets.items()}

    def _get_open_invoices(self, partner, as_of_date, move_type='out_invoice'):
        """Return open invoices as of a given date with running balance."""
        invoices = self.env['account.move'].search([
            ('partner_id', '=', partner.id),
            ('move_type', '=', move_type),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
            ('invoice_date', '<=', as_of_date),
        ], order='invoice_date asc')
        lines = []
        running = 0.0
        for inv in invoices:
            running += round(inv.amount_residual, 2)
            lines.append({
                'date': inv.invoice_date,
                'reference': inv.name,
                'original_amount': round(inv.amount_total, 2),
                'open_amount': round(inv.amount_residual, 2),
                'balance': round(running, 2),
            })
        return lines, round(running, 2)

    def _get_activity_data(self, partner, start_date, end_date, move_type='out_invoice', refund_type='out_refund', account_type='asset_receivable'):
        """Return invoices with their reconciled payment sub-lines."""
        is_vendor = move_type == 'in_invoice'
        domain = [
            ('partner_id', '=', partner.id),
            ('move_type', 'in', [move_type, refund_type]),
            ('state', '=', 'posted'),
        ]
        if start_date:
            domain.append(('invoice_date', '>=', start_date))
        if end_date:
            domain.append(('invoice_date', '<=', end_date))
        invoices = self.env['account.move'].search(domain, order='invoice_date asc')

        opening_balance = 0.0
        if start_date:
            prior_date = (datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date) - timedelta(days=1)
            _, opening_balance = self._get_open_invoices(partner, prior_date, move_type)
        running = 0.0

        lines = []
        for inv in invoices:
            is_refund = inv.move_type == 'out_refund'
            original = round(inv.amount_total, 2)
            applied = round(inv.amount_total - inv.amount_residual, 2)
            open_amount = round(inv.amount_residual, 2)
            running += original if not is_refund else -original

            sub_lines = []
            for line in inv.line_ids.filtered(lambda l: l.account_id.account_type == account_type):
                for partial in (line.matched_debit_ids if is_vendor else line.matched_credit_ids):
                    pmt_move = partial.debit_move_id.move_id if is_vendor else partial.credit_move_id.move_id
                    pmt_date = partial.debit_move_id.date if is_vendor else partial.credit_move_id.date
                    memo = pmt_move.ref or ''
                    ref = f'Payment for {inv.name}'
                    if memo:
                        ref += f', Ref: {memo}'
                    running -= round(partial.amount, 2)
                    sub_lines.append({
                        'date': pmt_date,
                        'reference': ref,
                        'applied_amount': round(partial.amount, 2),
                    })

            lines.append({
                'date': inv.invoice_date,
                'reference': inv.name,
                'original_amount': -original if is_refund else original,
                'applied_amount': applied,
                'open_amount': -open_amount if is_refund else open_amount,
                'balance': round(running, 2),
                'sub_lines': sub_lines,
            })

        closing_balance = round(opening_balance + running, 2)
        return lines, closing_balance, round(opening_balance, 2)

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company
        currency_symbol = company.currency_id.symbol
        form = data.get('form_data')
        statement_type = form.get('statement_type', 'outstanding')
        start_date = form.get('start_date')
        end_date = form.get('end_date')
        partner_ids = form.get('partner_ids')
        partner_type = form.get('partner_type', 'customer')
        move_type = 'out_invoice' if partner_type == 'customer' else 'in_invoice'
        refund_type = 'out_refund' if partner_type == 'customer' else 'in_refund'
        account_type = 'asset_receivable' if partner_type == 'customer' else 'liability_payable'
        exclude_zero_balance = form.get('exclude_zero_balance', False)
        show_aging_buckets = form.get('show_aging_buckets', True)
        aging_type = form.get('aging_type', 'days')
        as_of_date_str = form.get('as_of_date')
        as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date() if as_of_date_str else date.today()

        def fmt(amount):
            return '{:,.2f}'.format(amount)

        partners_data = []
        for partner in self.env['res.partner'].browse(partner_ids):
            if statement_type in ('activity', 'detailed_activity'):
                lines, closing_balance, opening_bal = self._get_activity_data(partner, start_date, end_date, move_type, refund_type, account_type)
                if exclude_zero_balance and closing_balance == 0:
                    continue

                prior_lines = ending_lines = []
                prior_balance = ending_balance = '0.00'
                fmt_buckets = {'_has_balance': False}
                if statement_type == 'detailed_activity' and start_date:
                    prior_date = (datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date) - timedelta(days=1)
                    end = datetime.strptime(end_date, '%Y-%m-%d').date() if isinstance(end_date, str) and end_date else as_of_date
                    raw_prior, prior_bal = self._get_open_invoices(partner, prior_date, move_type)
                    raw_ending, ending_bal = self._get_open_invoices(partner, end, move_type)
                    prior_lines = [{
                        'date': l['date'], 'reference': l['reference'],
                        'original_amount': fmt(l['original_amount']),
                        'open_amount': fmt(l['open_amount']),
                        'balance': fmt(l['balance']),
                    } for l in raw_prior]
                    ending_lines = [{
                        'date': l['date'], 'reference': l['reference'],
                        'original_amount': fmt(l['original_amount']),
                        'open_amount': fmt(l['open_amount']),
                        'balance': fmt(l['balance']),
                    } for l in raw_ending]
                    prior_balance = fmt(prior_bal)
                    ending_balance = fmt(ending_bal)

                    raw_buckets = self._get_aging_buckets(partner, aging_type, end, move_type)
                    fmt_buckets = {k: fmt(v) for k, v in raw_buckets.items()}
                    fmt_buckets['_has_balance'] = raw_buckets.get('total', 0) != 0 and show_aging_buckets

                if statement_type == 'activity':
                    raw_buckets = self._get_aging_buckets(partner, aging_type, as_of_date, move_type)
                    fmt_buckets = {k: fmt(v) for k, v in raw_buckets.items()}
                    fmt_buckets['_has_balance'] = raw_buckets.get('total', 0) != 0 and show_aging_buckets
                    opening_balance = fmt(opening_bal)

                partners_data.append({
                    'partner_name': partner.name,
                    'partner_street': partner.street,
                    'partner_street2': partner.street2,
                    'partner_zip': partner.zip,
                    'partner_city': partner.city,
                    'partner_state_id': partner.state_id.name,
                    'partner_country_id': partner.country_id.name,
                    'prior_lines': prior_lines,
                    'prior_balance': prior_balance,
                    'ending_lines': ending_lines,
                    'ending_balance': ending_balance,
                    'aging_buckets': fmt_buckets,
                    'lines': [{
                        'date': l['date'],
                        'reference': l['reference'],
                        'original_amount': fmt(l['original_amount']),
                        'applied_amount': fmt(l['applied_amount']),
                        'open_amount': fmt(l['open_amount']),
                        'balance': fmt(l['balance']),
                        'sub_lines': [{
                            'date': s['date'],
                            'reference': s['reference'],
                            'applied_amount': fmt(s['applied_amount']),
                        } for s in l['sub_lines']],
                    } for l in lines],
                    'closing_balance': fmt(closing_balance),
                    'opening_balance': opening_balance if statement_type == 'activity' else '0.00',
                    'partner_record': partner,
                })
            else:
                domain = [
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', move_type),
                ]
                if start_date:
                    domain.append(('invoice_date', '>=', start_date))
                if end_date:
                    domain.append(('invoice_date', '<=', end_date))
                invoices = self.env['account.move'].search(domain)
                invoice_data = []
                total_amount = total_payment = total_balance = 0
                for invoice in invoices:
                    paid_amount = invoice.amount_total - invoice.amount_residual
                    invoice_data.append({
                        'invoice_date': invoice.invoice_date,
                        'invoice_id': invoice.name,
                        'amount': fmt(invoice.amount_total),
                        'payment_amount': fmt(paid_amount),
                        'balance_due': fmt(invoice.amount_residual),
                    })
                    total_amount += invoice.amount_total
                    total_payment += paid_amount
                    total_balance += invoice.amount_residual

                if exclude_zero_balance and round(total_balance, 2) == 0:
                    continue

                raw_buckets = self._get_aging_buckets(partner, aging_type, as_of_date, move_type)
                fmt_buckets = {k: fmt(v) for k, v in raw_buckets.items()}
                fmt_buckets['_has_balance'] = raw_buckets.get('total', 0) != 0 and show_aging_buckets

                partners_data.append({
                    'partner_name': partner.name,
                    'partner_street': partner.street,
                    'partner_street2': partner.street2,
                    'partner_zip': partner.zip,
                    'partner_city': partner.city,
                    'partner_state_id': partner.state_id.name,
                    'partner_country_id': partner.country_id.name,
                    'invoices': invoice_data,
                    'total_amount': fmt(total_amount),
                    'total_payment': fmt(total_payment),
                    'total_balance': fmt(total_balance),
                    'aging_buckets': fmt_buckets,
                    'partner_record': partner,
                })

        return {
            'docs': partners_data,
            'today_date': date.today(),
            'as_of_date': as_of_date,
            'start_date': datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) and start_date else start_date,
            'end_date': datetime.strptime(end_date, '%Y-%m-%d').date() if isinstance(end_date, str) and end_date else end_date,
            'currency': currency_symbol,
            'aging_type': aging_type,
            'statement_type': statement_type,
        }
