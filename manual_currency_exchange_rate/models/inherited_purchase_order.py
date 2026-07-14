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
from odoo.tools.float_utils import float_compare, float_round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    main_currency_exchange_rate = fields.Float(string='Main Currency Exchange Rate')
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate')
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)


    @api.onchange('main_currency_exchange_rate')
    def onchange_main_currency_exchange_rate(self):
        for order in self:
            order.manual_currency_exchange_rate = 0
            if order.main_currency_exchange_rate:
                order.manual_currency_exchange_rate = 1.00 / order.main_currency_exchange_rate

    @api.onchange('company_id','currency_id')
    def onchange_currency_id(self):
        if self.company_id or self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res.update({
            'apply_manual_currency_exchange':self.apply_manual_currency_exchange,
            'manual_currency_exchange_rate':self.manual_currency_exchange_rate,
            'main_currency_exchange_rate':self.main_currency_exchange_rate,
            'active_manual_currency_rate':self.active_manual_currency_rate
            })
        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # New code
    @api.depends('product_qty', 'product_uom_id', 'company_id', 'order_id.partner_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id:
                continue
            params = line._get_select_sellers_params()
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
                uom_id=line.product_uom_id,
                params=params)

            if seller or not line.date_planned:
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            # If not seller, use the standard price. It needs a proper currency conversion.
            if not seller:
                line.discount = 0
                unavailable_seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id == line.order_id.partner_id)
                if not unavailable_seller and line.price_unit and line.product_uom_id == line._origin.product_uom_id:
                    # Avoid to modify the price unit if there is no price list for this partner and
                    # the line has already one to avoid to override unit price set manually.
                    continue
                po_line_uom = line.product_uom_id or line.product_id.uom_po_id
                price_unit = line.env['account.tax']._fix_tax_included_price_company(
                    line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                    line.product_id.supplier_taxes_id,
                    line.tax_ids,
                    line.company_id,
                )
                if line.order_id.apply_manual_currency_exchange:
                    price_unit = price_unit * line.order_id.manual_currency_exchange_rate
                else:
                    price_unit = line.product_id.cost_currency_id._convert(
                        price_unit,
                        line.currency_id,
                        line.company_id,
                        line.date_order or fields.Date.context_today(line),
                        False
                    )
                line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places, self.env['decimal.precision'].precision_get('Product Price')))

            elif seller:
                price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price, line.product_id.supplier_taxes_id, line.tax_ids, line.company_id) if seller else 0.0
                if line.order_id.apply_manual_currency_exchange:
                    line.price_unit = price_unit * line.order_id.manual_currency_exchange_rate
                else:
                    price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id, line.date_order or fields.Date.context_today(line), False)
                    price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places, self.env['decimal.precision'].precision_get('Product Price')))
                    line.price_unit = seller.product_uom._compute_price(price_unit, line.product_uom_id)
                line.discount = seller.discount or 0.0

            # record product names to avoid resetting custom descriptions
            default_names = []
            vendors = line.product_id._prepare_sellers({})
            product_ctx = {'seller_id': None, 'partner_id': None, 'lang': get_lang(line.env, line.partner_id.lang).code}
            default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            for vendor in vendors:
                product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            if not line.name or line.name in default_names:
                product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        if self.order_id.apply_manual_currency_exchange:
            price_unit = self.price_unit / self.order_id.manual_currency_exchange_rate
        return super(PurchaseOrderLine,self)._prepare_stock_move_vals(picking,price_unit,product_uom_qty,product_uom)
