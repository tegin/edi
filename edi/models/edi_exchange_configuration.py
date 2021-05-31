# Copyright 2021 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)
try:
    import yaml
except ImportError:
    _logger.error("YAML library cannot be found")


class EdiExchangeConfiguration(models.Model):
    _name = "edi.exchange.configuration"
    _description = "Edi Exchange Configuration"

    res_id = fields.Many2oneReference(model_field="model", required=True)
    model = fields.Char(required=True,)
    backend_id = fields.Many2one("edi.backend", required=True,)
    exchange_type_id = fields.Many2one("edi.exchange.type", required=True,)
    usage_ids = fields.Many2many("edi.exchange.configuration.usage", required=True,)
    advanced_settings_edit = fields.Text(
        string="Advanced YAML settings",
        help="""
            Advanced technical settings as YAML format.
            The YAML structure should reproduce a dictionary.
            The backend might use these settings for automated operations.

            Currently supported conf:
                your_param: $your_param_value
            In any case, you can use these settings
            to provide your own configuration for whatever need you might have.
        """,
    )

    def _load_advanced_settings(self):
        return yaml.safe_load(self.advanced_settings_edit or "") or {}

    def _generate_exchange_record(self, record=False):
        exchange_type = self.exchange_type_id
        backend = self.backend_id
        if record and hasattr(record, "_check_edi_configuration"):
            if not record._check_edi_configuration(exchange_type):
                return
        params = self._load_advanced_settings()
        vals = {}
        if record:
            vals.update({"model": record._name, "res_id": record.id, "params": params})
        return backend.create_record(exchange_type.code, vals)
