from odoo import models, api, fields
from odoo.exceptions import UserError

class PartnerStatementReport(models.AbstractModel):
    _name = 'report.customer_statement_filter.report_details'
    _description = 'Customer Statement Logic'

    @api.model
    def _get_report_values(self, docids, data=None):
        # If triggered from the wizard, docids will be passed here
        if not docids and data.get('context'):
            docids = data['context'].get('active_ids')

        partners = self.env['res.partner'].browse(docids)
        
        if not partners:
            raise UserError("No customers selected for the statement.")

        return {
            'doc_ids': docids,
            'doc_model': 'res.partner',
            'docs': partners,
            # We pass the data dictionary so the XML can see date_from/date_to
            'data': data,
        }