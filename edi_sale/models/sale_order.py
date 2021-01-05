# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "edi.exchange.consumer.mixin"]

    def name_get(self):
        """Add amount_untaxed in name_get of sale orders"""
        res = super().name_get()
        if self._context.get("sale_order_show_amount"):
            new_res = []
            for (sale_id, name) in res:
                sale = self.browse(sale_id)
                # I didn't find a python method to easily display
                # a float + currency symbol (before or after)
                # depending on lang of context and currency
                name += _(" Amount w/o tax: %s %s)") % (
                    sale.amount_untaxed,
                    sale.currency_id.name,
                )
                new_res.append((sale_id, name))
            return new_res
        else:
            return res
