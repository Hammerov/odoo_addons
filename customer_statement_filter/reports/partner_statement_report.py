from odoo import models, api, fields
from odoo.exceptions import UserError

class PartnerStatementReport(models.AbstractModel):
    _name = 'report.customer_statement_filter.report_details'
    _description = 'Customer Statement Logic'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}

        if not docids and data.get('context'):
            docids = data['context'].get('active_ids')

        partners = self.env['res.partner'].browse(docids)

        if not partners:
            raise UserError("No customers selected for the statement.")

        date_from = fields.Date.to_date(data.get('date_from')) if data.get('date_from') else False
        date_to = fields.Date.to_date(data.get('date_to')) if data.get('date_to') else False
        exclude_zero_balance = bool(data.get('exclude_zero_balance'))
        account_id = data.get('account_id')
        statement_type = data.get('statement_type') or 'detailed'

        partner_statements = []
        for partner in partners:
            domain = [
                ('partner_id', '=', partner.id),
                ('account_id.account_type', '=', 'asset_receivable'),
                ('parent_state', '=', 'posted'),
            ]
            if account_id:
                domain.append(('account_id', '=', account_id))
            if date_to:
                domain.append(('date', '<=', date_to))

            all_lines = self.env['account.move.line'].search(domain, order='date asc, id asc')
            if statement_type == 'summary' and date_from:
                lines_in_period = all_lines.filtered(lambda l: l.date >= date_from)
                opening_balance = sum((line.debit - line.credit) for line in all_lines if line.date < date_from)
            else:
                # Detailed mode prints full history; running balance starts from first line.
                lines_in_period = all_lines
                opening_balance = 0.0
            running_balance = opening_balance
            line_rows = []
            for line in lines_in_period:
                amount = line.debit - line.credit
                running_balance += amount
                line_rows.append({
                    'line': line,
                    'amount': amount,
                    'running_balance': running_balance,
                })

            ending_balance = running_balance
            if exclude_zero_balance and not ending_balance:
                continue

            partner_statements.append({
                'partner': partner,
                'opening_balance': opening_balance,
                'lines': line_rows,
                'ending_balance': ending_balance,
            })

        if not partner_statements:
            raise UserError("No customers matched the selected filters.")

        return {
            'doc_ids': docids,
            'doc_model': 'res.partner',
            'docs': partners,
            'partner_statements': partner_statements,
            'data': data,
        }