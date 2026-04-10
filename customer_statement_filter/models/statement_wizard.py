from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CustomerStatementWizard(models.TransientModel):
    _name = 'customer.statement.wizard'
    _description = 'Customer Statement Wizard'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    account_id = fields.Many2one('account.account', string='A/R Account', 
                                 domain=[('account_type', '=', 'asset_receivable')])
    partner_ids = fields.Many2many('res.partner', string='Select Customers')
    exclude_zero_balance = fields.Boolean(string='Exclude Zero Balances', default=True)

    def action_print_statements(self):
        self.ensure_one()
        
        # Build the domain for partners
        domain = [('id', 'in', self.partner_ids.ids)]
        if self.exclude_zero_balance:
            domain.append(('total_due', '>', 0))
            
        partners = self.env['res.partner'].search(domain)
        
        if not partners:
            raise UserError(_("No customers found with the selected criteria."))

        # Triggering the native Odoo Follow-up report engine
        return self.env.ref('account_followup.action_report_followup').report_action(partners)
