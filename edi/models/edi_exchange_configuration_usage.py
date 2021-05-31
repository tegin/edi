# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EdiExchangeConfigurationUsage(models.Model):
    _name = "edi.exchange.configuration.usage"
    _description = "Edi Configuration Usage"

    name = fields.Char(required=True)

    _sql_constraints = [("name_unique", "UNIQUE(name)", "Name must be unique")]
