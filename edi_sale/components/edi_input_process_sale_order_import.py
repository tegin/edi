# Copyright 2020 Creu Blanca
# @author: Enric Tobella
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero

from odoo.addons.component.core import Component


class EdiInputProcessSaleOrderImport(Component):
    """Generate a Sale Order from a JSON"""

    _name = "edi.input.process.sale_order_import"
    _usage = "edi.input.process.sale_order_import"
    _inherit = "edi.component.input.mixin"

    def process(self):
        parsed_order = json.loads(self.exchange_record._get_file_content())
        if self.backend.env.context.get("update_sale_order", False):
            order = self._update_order(parsed_order)
        else:
            order = self._create_order(parsed_order)
        self.exchange_record.write({"model": order._name, "res_id": order.id})

    def _create_order_vals(self, parsed_order):
        # TODO: Remove the on_play_changes and change it for the form directly
        soo = self.env["sale.order"]
        bdio = self.env["business.document.import"]
        price_source = self.exchange_record.record.price_source
        partner = bdio._match_partner(
            parsed_order["partner"],
            parsed_order["chatter_msg"],
            partner_type="customer",
        )
        currency = bdio._match_currency(
            parsed_order.get("currency"), parsed_order["chatter_msg"]
        )
        if partner.property_product_pricelist.currency_id != currency:
            raise UserError(
                _(
                    "The customer '%s' has a pricelist '%s' but the "
                    "currency of this order is '%s'."
                )
                % (
                    partner.display_name,
                    partner.property_product_pricelist.display_name,
                    currency.name,
                )
            )
        if parsed_order.get("order_ref"):
            commercial_partner = partner.commercial_partner_id
            existing_orders = soo.search(
                [
                    ("client_order_ref", "=", parsed_order["order_ref"]),
                    ("commercial_partner_id", "=", commercial_partner.id),
                    ("state", "!=", "cancel"),
                ]
            )
            if existing_orders:
                raise UserError(
                    _(
                        "An order of customer '%s' with reference '%s' "
                        "already exists: %s (state: %s)"
                    )
                    % (
                        partner.display_name,
                        parsed_order["order_ref"],
                        existing_orders[0].name,
                        existing_orders[0].state,
                    )
                )

        so_vals = {
            "partner_id": partner.id,
            "client_order_ref": parsed_order.get("order_ref"),
        }
        so_vals = soo.play_onchanges(so_vals, ["partner_id"])
        so_vals["order_line"] = []
        if parsed_order.get("ship_to"):
            shipping_partner = bdio._match_shipping_partner(
                parsed_order["ship_to"], partner, parsed_order["chatter_msg"]
            )
            so_vals["partner_shipping_id"] = shipping_partner.id
        if parsed_order.get("invoice_to"):
            invoicing_partner = bdio._match_partner(
                parsed_order["partner"], parsed_order["chatter_msg"], partner_type=""
            )
            so_vals["partner_invoice_id"] = invoicing_partner.id
        if parsed_order.get("date"):
            so_vals["date_order"] = parsed_order["date"]
        for line in parsed_order["lines"]:
            # partner=False because we don't want to use product.supplierinfo
            product = bdio._match_product(
                line["product"], parsed_order["chatter_msg"], seller=False
            )
            uom = bdio._match_uom(line.get("uom"), parsed_order["chatter_msg"], product)
            line_vals = self._prepare_create_order_line(
                product, uom, so_vals, line, price_source
            )
            so_vals["order_line"].append((0, 0, line_vals))
        return so_vals

    def _prepare_create_order_line(
        self, product, uom, order, import_line, price_source
    ):
        """the 'order' arg can be a recordset (in case of an update of a sale order)
        or a dict (in case of the creation of a new sale order)"""
        solo = self.env["sale.order.line"]
        vals = {
            "product_id": product.id,
            "product_uom_qty": import_line["qty"],
            "product_uom": uom.id,
        }
        if price_source == "order":
            vals["price_unit"] = import_line["price_unit"]  # TODO : fix
        elif price_source == "pricelist":
            # product_id_change is played in the inherit of create()
            # of sale.order.line cf odoo/addons/sale/models/sale.py
            # but it is not enough: we also need to play _onchange_discount()
            # to have the right discount for pricelist
            vals["order_id"] = order
            vals = solo.play_onchanges(vals, ["product_id"])
            vals.pop("order_id")
        return vals

    def _create_order(self, parsed_order):
        order = self.env["sale.order"].create(self._create_order_vals(parsed_order))
        order.message_post(
            body=_("Created automatically via file import (%s).")
            % self.exchange_record.record.order_filename
        )
        return order

    def _update_order(self, parsed_order):
        record = self.exchange_record.record
        order = record.sale_id
        order.ensure_one()
        bdio = self.env["business.document.import"]
        currency = bdio._match_currency(
            parsed_order.get("currency"), parsed_order["chatter_msg"]
        )

        if currency != order.currency_id:
            raise UserError(
                _(
                    "The currency of the imported order (%s) is different from "
                    "the currency of the existing order (%s)"
                )
                % (currency.name, order.currency_id.name)
            )
        vals = self._prepare_update_order_vals(
            parsed_order, order, record.commercial_partner_id
        )
        if vals:
            order.write(vals)
        self._update_order_lines(parsed_order, order, record.price_source)
        bdio.post_create_or_update(parsed_order, order)
        order.message_post(
            body=_(
                "This quotation has been updated automatically via the import of "
                "file %s"
            )
            % record.order_filename
        )
        return order

    def _prepare_update_order_vals(self, parsed_order, order, partner):
        bdio = self.env["business.document.import"]
        partner = bdio._match_partner(
            parsed_order["partner"],
            parsed_order["chatter_msg"],
            partner_type="customer",
        )
        vals = {"partner_id": partner.id}
        if parsed_order.get("ship_to"):
            shipping_partner = bdio._match_shipping_partner(
                parsed_order["ship_to"], partner, parsed_order["chatter_msg"]
            )
            vals["partner_shipping_id"] = shipping_partner.id
        if parsed_order.get("order_ref"):
            vals["client_order_ref"] = parsed_order["order_ref"]
        return vals

    def _update_order_lines(self, parsed_order, order, price_source):
        chatter = parsed_order["chatter_msg"]
        solo = self.env["sale.order.line"]
        dpo = self.env["decimal.precision"]
        bdio = self.env["business.document.import"]
        qty_prec = dpo.precision_get("Product UoS")
        price_prec = dpo.precision_get("Product Price")
        existing_lines = []
        for oline in order.order_line:
            # compute price unit without tax
            price_unit = 0.0
            if not float_is_zero(oline.product_uom_qty, precision_digits=qty_prec):
                qty = float(oline.product_uom_qty)
                price_unit = oline.price_subtotal / qty
            existing_lines.append(
                {
                    "product": oline.product_id or False,
                    "name": oline.name,
                    "qty": oline.product_uom_qty,
                    "uom": oline.product_uom,
                    "line": oline,
                    "price_unit": price_unit,
                }
            )
        compare_res = bdio.compare_lines(
            existing_lines,
            parsed_order["lines"],
            chatter,
            qty_precision=qty_prec,
            seller=False,
        )
        # NOW, we start to write/delete/create the order lines
        for oline, cdict in compare_res["to_update"].items():
            write_vals = {}
            # TODO: add support for price_source == order
            if cdict.get("qty"):
                chatter.append(
                    _(
                        "The quantity has been updated on the order line "
                        "with product '%s' from %s to %s %s"
                    )
                    % (
                        oline.product_id.display_name,
                        cdict["qty"][0],
                        cdict["qty"][1],
                        oline.product_uom.name,
                    )
                )
                write_vals["product_uom_qty"] = cdict["qty"][1]
                if price_source != "order":
                    new_price_unit = order.pricelist_id.with_context(
                        date=order.date_order, uom=oline.product_uom.id
                    ).price_get(
                        oline.product_id.id,
                        write_vals["product_uom_qty"],
                        order.partner_id.id,
                    )[
                        order.pricelist_id.id
                    ]
                    if float_compare(
                        new_price_unit, oline.price_unit, precision_digits=price_prec
                    ):
                        chatter.append(
                            _(
                                "The unit price has been updated on the order "
                                "line with product '%s' from %s to %s %s"
                            )
                            % (
                                oline.product_id.display_name,
                                oline.price_unit,
                                new_price_unit,
                                order.currency_id.name,
                            )
                        )
                        write_vals["price_unit"] = new_price_unit
            if write_vals:
                oline.write(write_vals)
        if compare_res["to_remove"]:
            to_remove_label = [
                "%s %s x %s"
                % (line.product_uom_qty, line.product_uom.name, line.product_id.name)
                for line in compare_res["to_remove"]
            ]
            chatter.append(
                _("%d order line(s) deleted: %s")
                % (len(compare_res["to_remove"]), ", ".join(to_remove_label))
            )
            compare_res["to_remove"].unlink()
        if compare_res["to_add"]:
            to_create_label = []
            for add in compare_res["to_add"]:
                line_vals = self._prepare_create_order_line(
                    add["product"], add["uom"], order, add["import_line"], price_source
                )
                line_vals["order_id"] = order.id
                new_line = solo.create(line_vals)
                to_create_label.append(
                    "%s %s x %s"
                    % (
                        new_line.product_uom_qty,
                        new_line.product_uom.name,
                        new_line.name,
                    )
                )
            chatter.append(
                _("%d new order line(s) created: %s")
                % (len(compare_res["to_add"]), ", ".join(to_create_label))
            )
        return True
