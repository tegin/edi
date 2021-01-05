# Copyright 2020 Creu Blanca
# @author: Enric Tobella
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import Component


class EdiInputProcessSaleOrderImportXML(Component):
    """Parses a Sale Order from an XML. It must follow:
    {
        'partner': {
            'vat': 'FR25499247138',
            'name': 'Camptocamp',
            'email': 'luc@camptocamp.com',
        },
        'ship_to': {
            'partner': partner_dict,
            'address': {
                'country_code': 'FR',
                'state_code': False,
                'zip': False,
            },
        },
        'company': {'vat': 'FR12123456789'},  # Only used to check we are not
        # importing the order in the
        # wrong company by mistake
        'date': '2016-08-16',  # order date
        'order_ref': 'PO1242',  # Customer PO number
        'currency': {'iso': 'EUR', 'symbol': u'€'},
        'incoterm': 'EXW',
        'note': 'order notes of the customer',
        'chatter_msg': ['msg1', 'msg2']
        'lines': [{
            'product': {
            'code': 'EA7821',
            'ean13': '2100002000003',
        },
        'qty': 2.5,
        'uom': {'unece_code': 'C62'},
        'price_unit': 12.42,  # without taxes
        'doc_type': 'rfq' or 'order',
    }
    """

    _name = "edi.input.receive.sale_order_import.sale.order.import.xml"
    _usage = "edi.input.receive.sale_order_import.sale.order.import.xml"
    _inherit = "edi.component.receive.mixin"

    def receive(self, filename=False, file=False):
        record = self.exchange_record.record
        filename = filename or record.order_filename
        file = file or record.order_file
        return self._receive(filename, file)

    def _receive(self, filename, file):
        """This is a hook intended to be implemented according to specific needs"""
        raise UserError(
            _(
                "This type of XML RFQ/order is not supported. Did you install "
                "the module to support this XML format?"
            )
        )
