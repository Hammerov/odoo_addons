from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CustomerStatementWizard(models.TransientModel):
    _name = 'customer.statement.wizard'
    _description = 'Customer Statement Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    
    account_id = fields.Many2one('account.account', string='A/R Account', 
                                 domain=[('account_type', '=', 'asset_receivable')])
    
    exclude_zero_balance = fields.Boolean(string='Exclude Zero Balances', default=True)
    
    # THIS IS THE MISSING FIELD
    statement_type = fields.Selection([
        ('summary', 'Balance Summary'),
        ('detailed', 'Full Transaction Details')
    ], string='Statement Style', default='summary')

    partner_ids = fields.Many2many('res.partner', string='Select Customers')

    def action_print_statements(self):
        self.ensure_one()
        partners = self.partner_ids if self.partner_ids else self.env['res.partner'].search([])
        if self.exclude_zero_balance:
            partners = partners.filtered(lambda p: p.total_due > 0)

        if not partners:
            raise UserError("No customers found.")

        # Pass the IDs directly to the report
        return self.env.ref('customer_statement_filter.action_report_custom_statement').report_action(partners.ids, data={
            'date_from': self.date_from,
            'date_to': self.date_to,
        })