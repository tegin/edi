# Copyright 2020 Creu Blanca
# @author: Enric Tobella
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component


class EdiInputProcessSaleOrderImport(Component):
    """Validates the JSON obtained when processing the file"""

    _name = "edi.input.validate.sale_order_import"
    _usage = "edi.input.validate.sale_order_import"
    _inherit = "edi.component.validate.mixin"

    def _validate(self, value=None):
        value = value or self.exchange_record._get_file_content()
        bdio = self.env["business.document.import"]
        parsed_order = json.loads(value)
        if not parsed_order.get("lines"):
            raise UserError(_("This order doesn't have any lines !"))
        partner = bdio._match_partner(
            parsed_order["partner"], [], partner_type="customer"
        )
        commercial_partner = partner.commercial_partner_id
        partner_shipping_id = False
        if parsed_order.get("ship_to"):
            partner_shipping_id = bdio._match_shipping_partner(
                parsed_order["ship_to"], partner, []
            ).id
        doc_type = parsed_order.get("doc_type")
        price_source = "order" if doc_type == "order" else False
        self.exchange_record.record.write(
            {
                "commercial_partner_id": commercial_partner.id,
                "partner_shipping_id": partner_shipping_id,
                "state": "update",
                "doc_type": doc_type,
                "price_source": price_source,
            }
        )
        self.exchange_record.write(
            {"external_identifier": parsed_order.get("order_ref")}
        )
