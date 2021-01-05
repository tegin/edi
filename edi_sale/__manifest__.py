# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Edi Sale",
    "summary": "Allow to manage sale orders as EDI",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "author": "Akretion,Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/edi",
    "depends": [
        "edi",
        "sale",
        "sale_commercial_partner",
        "base_business_document_import",
        # OCA/server-tools
        "onchange_helper",
    ],
    "data": ["wizards/sale_order_import.xml", "views/sale_order.xml", "data/edi.xml"],
}
