from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_round

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.constrains('product_uom_qty')
    def _check_quantity_integer(self):
        """Prevent saving any order line with a decimal quantity."""
        for line in self:
            rounded_qty = float_round(line.product_uom_qty, precision_digits=0)
            if float_compare(line.product_uom_qty, rounded_qty, precision_digits=6):
                raise ValidationError(
                    _(
                        "Quantity for '%(product)s' must be a whole number. "
                        "Value '%(quantity)s' is not allowed."
                    )
                    % {
                        'product': line.product_id.display_name,
                        'quantity': line.product_uom_qty,
                    }
                )