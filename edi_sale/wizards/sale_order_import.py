# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import mimetypes

from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrderImport(models.TransientModel):
    _name = "sale.order.import"
    _description = "Sale Order Import from Files"

    state = fields.Selection(
        [("import", "Import"), ("update", "Update")], string="State", default="import"
    )
    order_file = fields.Binary(
        string="Request for Quotation or Order",
        required=True,
        help="Upload a Request for Quotation or an Order file. Supported "
        "formats: CSV, XML and PDF (PDF with an embeded XML file).",
    )
    order_filename = fields.Char(string="Filename")
    doc_type = fields.Selection(
        [("rfq", "Request For Quotation"), ("order", "Sale Order")],
        string="Document Type",
        readonly=True,
    )
    price_source = fields.Selection(
        [("pricelist", "Pricelist"), ("order", "Customer Order")],
        string="Apply Prices From",
    )
    # for state = update
    commercial_partner_id = fields.Many2one(
        "res.partner", string="Commercial Entity", readonly=True
    )
    partner_shipping_id = fields.Many2one(
        "res.partner", string="Shipping Address", readonly=True
    )
    sale_id = fields.Many2one("sale.order", string="Quotation to Update")
    edi_exchange_record_id = fields.Many2one("edi.exchange.record")

    def edi_create_order_button(self):
        self.ensure_one()
        self.edi_exchange_record_id.ensure_one()
        exchange_record = self.edi_exchange_record_id
        assert exchange_record.edi_exchange_state == "input_received"
        exchange_record.backend_id.with_context(
            _edi_receive_break_on_error=True
        ).exchange_process(exchange_record)
        exchange_record.refresh()
        order = exchange_record.record
        order.message_post(
            body=_("Created automatically via file import (%s).") % self.order_filename
        )
        return self._get_sale_order_form(order)

    def _get_sale_order_form(self, order):
        action = self.env["ir.actions.act_window"].for_xml_id(
            "sale", "action_quotations"
        )
        action.update(
            {
                "view_mode": "form,tree,calendar,graph",
                "views": False,
                "view_id": False,
                "res_id": order.id,
            }
        )
        return action

    def update_order_button(self):
        self.ensure_one()
        if not self.sale_id:
            raise UserError(_("You must select a quotation to update."))
        self.edi_exchange_record_id.ensure_one()
        exchange_record = self.edi_exchange_record_id
        assert exchange_record.edi_exchange_state == "input_received"
        exchange_record.backend_id.with_context(
            _edi_receive_break_on_error=True, update_sale_order=True,
        ).exchange_process(exchange_record)
        exchange_record.refresh()
        order = exchange_record.record
        order.message_post(
            body=_("Created automatically via file import (%s).") % self.order_filename
        )
        return self._get_sale_order_form(order)

    def _get_exchange_type_code(self):
        filetype = mimetypes.guess_type(self.order_filename)
        if not filetype:
            pass
        elif filetype[0] in ["application/xml", "text/xml"]:
            return "sale.order.import.xml"
        elif filetype and filetype[0] == "application/pdf":
            return "sale.order.import.pdf"
        raise UserError(_("A exchange type record cannot be found"))

    def import_order_button(self):
        self.ensure_one()
        backend = self.env.ref("edi_sale.backend")
        exchange_record = backend.create_record(
            self._get_exchange_type_code(),
            {
                "model": self._name,
                "res_id": self.id,
                "edi_exchange_state": "input_pending",
            },
        )
        self.edi_exchange_record_id = exchange_record
        backend.with_context(_edi_receive_break_on_error=True).exchange_receive(
            exchange_record
        )
        existing_quotations = self.env["sale.order"].search(
            [
                ("commercial_partner_id", "=", self.commercial_partner_id.id),
                ("state", "in", ("draft", "sent")),
                ("client_order_ref", "=", exchange_record.external_identifier),
            ]
        )
        if existing_quotations:
            if len(existing_quotations) == 1:
                self.sale_id = existing_quotations
            action = self.env["ir.actions.act_window"].for_xml_id(
                "edi_sale", "sale_order_import_act_window"
            )
            action["res_id"] = self.id
            return action
        else:
            return self.edi_create_order_button()
