import ast
import operator
import re

from odoo import api, fields, models, _

_PACK_EXPR_PATTERN = re.compile(r"^[\d+\-*/().\s]+$")

_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_pack_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Invalid pack expression")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError("Unsupported operator")
        return _SAFE_OPERATORS[op_type](
            _eval_pack_node(node.left),
            _eval_pack_node(node.right),
        )
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError("Unsupported operator")
        return _SAFE_OPERATORS[op_type](_eval_pack_node(node.operand))
    raise ValueError("Invalid pack expression")


def parse_pack_quantity(pack_value):
    """Turn a pack expression such as '10*10' or '10' into a numeric quantity."""
    if pack_value is None:
        return None
    expr = str(pack_value).strip()
    if not expr:
        return None
    if not _PACK_EXPR_PATTERN.match(expr):
        raise ValueError(expr)
    normalized = expr.replace(" ", "")
    result = _eval_pack_node(ast.parse(normalized, mode="eval").body)
    if not isinstance(result, (int, float)):
        raise ValueError(expr)
    return result


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    pack = fields.Char(string="Packs", inverse="_inverse_pack")

    def _apply_pack_to_quantity(self, pack_value):
        qty = parse_pack_quantity(pack_value)
        if qty is not None:
            self.product_uom_qty = qty

    def _inverse_pack(self):
        for line in self:
            if line.pack:
                line._apply_pack_to_quantity(line.pack)

    @api.model
    def _pack_quantity_from_vals(self, vals):
        if not vals.get("pack"):
            return None
        try:
            return parse_pack_quantity(vals["pack"])
        except ValueError:
            return None

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            qty = self._pack_quantity_from_vals(vals)
            if qty is not None:
                vals["product_uom_qty"] = qty
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("pack"):
            try:
                vals = dict(vals, product_uom_qty=parse_pack_quantity(vals["pack"]))
            except ValueError:
                pass
        return super().write(vals)

    @api.onchange("pack")
    def _onchange_pack(self):
        if not self.pack:
            return
        try:
            self._apply_pack_to_quantity(self.pack)
        except ValueError:
            return {
                "warning": {
                    "title": _("Invalid pack expression"),
                    "message": _(
                        "Could not calculate quantity from '%(pack)s'. "
                        "Use numbers and operators such as +, -, *, /.",
                        pack=self.pack,
                    ),
                }
            }

    # This function tells Odoo to include 'pack' when converting a sale line to an invoice line
    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update({
            'pack': self.pack,
        })
        return res

    # Copies pack to delivery slip (stock move)
    def _prepare_procurement_values(self):
        vals = super()._prepare_procurement_values()
        vals['pack'] = self.pack
        return vals


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pack = fields.Char(string="Packs")


class StockMove(models.Model):
    _inherit = "stock.move"

    # Use a related field to "pull" the data from the sale line
    # Odoo's sale_stock module already provides the 'sale_line_id' link
    pack = fields.Char(
        string="Packs",
        related="sale_line_id.pack",
        readonly=True,
        store=True
    )
