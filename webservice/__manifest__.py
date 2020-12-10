# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Edi WebService",
    "summary": """
        Defines webservice integration from EDI Exchange records""",
    "version": "13.0.1.0.0",
    "license": "AGPL-3",
    "author": "Creu Blanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/edi",
    "depends": ["component", "server_environment"],
    "data": ["security/ir.model.access.csv", "views/webservice_backend.xml"],
    "demo": [],
}
