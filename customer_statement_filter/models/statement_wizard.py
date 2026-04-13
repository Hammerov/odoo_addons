from odoo import models, fields, _
from odoo.exceptions import UserError

class CustomerStatementWizard(models.TransientModel):
    _name = 'customer.statement.wizard'
    _description = 'Customer Statement Wizard'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    
    account_id = fields.Many2one('account.account', string='A/R Account', 
                                 domain=[('account_type', '=', 'asset_receivable')])
    
    exclude_zero_balance = fields.Boolean(string='Exclude Zero Balances', default=True)
    
    # THIS IS THE MISSING FIELD
    statement_type = fields.Selection([
        ('summary', 'Balance Summary'),
        ('detailed', 'Full Transaction Details')
    ], string='Statement Style', default='detailed')

    partner_ids = fields.Many2many(
        'res.partner',
        string='Select Customers',
        domain=[('customer_rank', '>', 0)],
    )

    def action_print_statements(self):
        self.ensure_one()
        partners = self.partner_ids if self.partner_ids else self.env['res.partner'].search([
            ('customer_rank', '>', 0),
        ])

        if not partners:
            raise UserError(_("No customers found for the selected filters."))

        # Report computes balances from posted receivable move lines.
        return self.env.ref('customer_statement_filter.action_report_custom_statement').report_action(partners.ids, data={
            'date_from': self.date_from,
            'date_to': self.date_to,
            'exclude_zero_balance': self.exclude_zero_balance,
            'account_id': self.account_id.id if self.account_id else False,
            'statement_type': self.statement_type,
        })