# Copyright 2020 ACSONE SA
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EDIExchangeConsumerMixin(models.AbstractModel):
    """
    Common features for models relying on EDI exchange records.
    """

    _name = "edi.exchange.consumer.mixin"
    _description = "EDI exchange consumer mixin"

    edi_exchange_record_ids = fields.One2many(
        comodel_name="edi.exchange.record",
        inverse_name="res_id",
        domain=lambda r: [("model", "=", r._name)],
    )

    def _action_view_exchance_records(self, **kw):
        action = {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "edi.exchange.record",
            "domain": [("res_id", "in", self.ids), ("model", "=", self._name)],
            "context": {"search_default_group_by_type_id": 1},
        }
        action.update(kw)
        return self._action_view_records()

    def action_view_records(self):
        self.ensure_one()
        return self._action_view_records()
