# Copyright 2020 Creu Blanca
# @author: Enric Tobella
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import json
import logging

from lxml import etree

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component

logger = logging.getLogger(__name__)


class EdiInputProcessSaleOrderImportPDF(Component):
    """Generate a Sale Order"""

    _name = "edi.input.receive.sale_order_import.sale.order.import.pdf"
    _usage = "edi.input.receive.sale_order_import.sale.order.import.pdf"
    _inherit = "edi.component.receive.mixin"

    def receive(self):
        record = self.exchange_record.record
        xml_files_dict = self.env["business.document.import"].get_xml_files_from_pdf(
            base64.b64decode(record.order_file)
        )
        if not xml_files_dict:
            raise UserError(_("There are no embedded XML file in this PDF file."))
        for xml_filename, xml_root in xml_files_dict.items():
            logger.info("Trying to parse XML file %s", xml_filename)
            try:
                parsed_order = self.component(
                    usage="edi.input.receive.sale_order_import.sale.order.import.xml"
                ).receive(xml_filename, xml_root)
                return json.dumps(parsed_order)
            except (etree.LxmlError, UserError):
                continue
        raise UserError(
            _(
                "This type of XML RFQ/order is not supported. Did you install "
                "the module to support this XML format?"
            )
        )
