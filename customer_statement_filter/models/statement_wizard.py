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
        
        # 1. Start with the selected partners or all customers
        if self.partner_ids:
            partners = self.partner_ids
        else:
            # If no specific customers are picked, look for all customers
            partners = self.env['res.partner'].search([])

        # 2. Filter by balance using Python (since total_due is not stored in SQL)
        if self.exclude_zero_balance:
            # We use .filtered() because it can handle non-stored computed fields
            partners = partners.filtered(lambda p: p.total_due > 0)
            
        if not partners:
            raise UserError(_("No customers found with the selected criteria."))

        # 3. Trigger the report
        return self.env.ref('account_followup.action_report_followup').report_action(partners)
    