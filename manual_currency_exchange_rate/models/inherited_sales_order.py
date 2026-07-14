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


class SalesOrder(models.Model):
    _inherit = 'sale.order'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    main_currency_exchange_rate = fields.Float(string='Main Currency Exchange Rate')
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Company Currency')
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)
    
    
    @api.onchange('main_currency_exchange_rate')
    def onchange_main_currency_exchange_rate(self):
        for order in self:
            order.manual_currency_exchange_rate = 0
            if order.main_currency_exchange_rate:
                order.manual_currency_exchange_rate = 1.00 / order.main_currency_exchange_rate
                
    
    def _prepare_invoice(self):
        result = super(SalesOrder, self)._prepare_invoice()
        result.update({
            'active_manual_currency_rate':self.active_manual_currency_rate,
            'apply_manual_currency_exchange':self.apply_manual_currency_exchange,
            'manual_currency_exchange_rate':self.manual_currency_exchange_rate,
            'main_currency_exchange_rate':self.main_currency_exchange_rate,
            })
        return result

    @api.onchange('company_currency_id', 'currency_id')
    def onchange_currency_id(self):
        if self.company_currency_id or self.currency_id:
            if self.company_currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # New Code
    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            # Don't compute the price for deleted lines.
            if line.order_id.active_manual_currency_rate:
                line = line.with_context(
                        manual_rate=line.order_id.manual_currency_exchange_rate,
                        active_manutal_currency=line.order_id.apply_manual_currency_exchange,
                    )
            if not line.order_id:
                continue
            # check if the price has been manually set or there is already invoiced amount.
            # if so, the price shouldn't change as it might have been manually edited.
            if (
                (line.technical_price_unit != line.price_unit and not line.env.context.get('force_price_recomputation'))
                or line.qty_invoiced > 0
                or (line.product_id.expense_policy == 'cost' and line.is_expense)
            ):
                continue
            if not line.product_uom_id or not line.product_id:
                line.price_unit = 0.0
                line.technical_price_unit = 0.0
            else:
                line = line.with_company(line.company_id)
                price = line._get_display_price()
                line.price_unit = line.product_id._get_tax_included_unit_price_from_price(
                    price,
                    product_taxes=line.product_id.taxes_id.filtered(
                        lambda tax: tax.company_id == line.env.company
                    ),
                    fiscal_position=line.order_id.fiscal_position_id,
                )
                line.technical_price_unit = line.price_unit
