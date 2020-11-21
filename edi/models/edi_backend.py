# Copyright 2020 ACSONE SA
# Copyright 2020 Creu Blanca
# @author Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import base64
import logging

from odoo import _, exceptions, fields, models, tools

_logger = logging.getLogger(__name__)


class EDIBackend(models.Model):
    """Generic backend to control EDI exchanges.

    Backends can be organized with types.
    """

    _name = "edi.backend"
    _description = "EDI Backend"
    _inherit = ["collection.base"]

    name = fields.Char(required=True)
    backend_type_id = fields.Many2one(
        string="EDI Backend type",
        comodel_name="edi.backend.type",
        required=True,
        ondelete="restrict",
    )

    def _get_component(self, safe=False, work_ctx=None, **kw):
        """Retrieve components for current backend.

        :param safe: boolean, if true does not break if component is not found
        :param work_ctx: dictionary with work context params
        :param kw: keyword args to lookup for components (eg: usage)
        """
        work_ctx = work_ctx or {}
        with self.work_on(self._name, **work_ctx) as work:
            if safe:
                component = work.many_components(**kw)
                return component[0] if component else None
            return work.component(**kw)

    def create_record(self, type_code, values):
        """Create an exchange record for current backend.

        :param type_code: edi.exchange.type code
        :param values: edi.exchange.record values
        :return: edi.exchange.record record
        """
        self.ensure_one()
        export_type = self.env["edi.exchange.type"].search(
            [("code", "=", type_code), ("backend_id", "=", self.id)], limit=1
        )
        export_type.ensure_one()
        values["type_id"] = export_type.id
        return self.env["edi.exchange.record"].create(values)

    def exchange_send(self, exchange_record):
        """Send exchange file."""
        self.ensure_one()
        exchange_record.ensure_one()
        if not exchange_record.direction != "outbound":
            raise exceptions.UserError(
                _("Record ID=%d is not meant to be sended") % exchange_record.id
            )
        if not exchange_record.exchange_file:
            raise exceptions.UserError(
                _("Record ID=%d has no file to send!") % exchange_record.id
            )
        # In case already sent: skip sending and check the state
        check = self._exchange_output_check(exchange_record)
        if not check:
            return False
        try:
            self._exchange_send(exchange_record)
        except Exception as err:
            error = str(err)
            state = "output_error_on_send"
            message = exchange_record._exchange_send_error_msg()
            res = False
        else:
            message = exchange_record._exchange_sent_msg()
            error = None
            state = "output_sent"
            res = True
        finally:
            exchange_record.edi_exchange_state = state
            exchange_record.exchange_error = error
            if message:
                self._exchange_notify_record(exchange_record, message)
        return res

    def _exchange_output_check(self, record):
        return record.edi_exchange_state in ["output_pending", "output_error_on_send"]

    def _exchange_send(self, exchange_record):
        # TODO: Maybe we could contact to the component here. Isn't it?
        raise NotImplementedError()

    def _exchange_notify_record(self, record, message, level="info"):
        """Attach exported file to original record."""
        if not hasattr(record.record, "message_post_with_view"):
            return
        record.record.message_post_with_view(
            "base_edi_exchange.message_edi_exchange_link",
            values={
                "backend": self,
                "exchange_record": record,
                "message": message,
                "level": level,
            },
            subtype_id=self.env.ref("mail.mt_note").id,
        )

    def _exchange_input_check(self, record):
        return record.edi_exchange_state in ["input_received", "input_processed_error"]

    def exchange_process(self, exchange_record):
        """
        This function should be called when an exchange record has been received
        it could integrate check where to relate or modificate the data
        """
        self.ensure_one()
        exchange_record.ensure_one()
        if not exchange_record.direction != "inbound":
            raise exceptions.UserError(
                _("Record ID=%d is not meant to be processed") % exchange_record.id
            )
        if not exchange_record.exchange_file:
            raise exceptions.UserError(
                _("Record ID=%d has no file to process!") % exchange_record.id
            )
        # In case already processed: skip processing and check the state
        check = self._exchange_input_check(exchange_record)
        if not check:
            return False
        try:
            self._exchange_process(exchange_record)
        except Exception as err:
            error = str(err)
            state = "input_processed_error"
            message = exchange_record._exchange_processed_ko_msg()
            res = False
        else:
            message = exchange_record._exchange_processed_ok_msg()
            error = None
            state = "input_processed"
            res = True
        finally:
            exchange_record.edi_exchange_state = state
            exchange_record.exchange_error = error
            if message:
                self._exchange_notify_record(exchange_record, message)
        return res

    def _exchange_process(self, exchange_record):
        # TODO: Maybe we could contact to the component here. Isn't it?
        raise NotImplementedError()

    def generate_output(self, exchange_record, store=True, **kw):
        self.ensure_one()
        exchange_record.ensure_one()
        if exchange_record.edi_exchange_state != "new":
            raise exceptions.UserError(
                _("Record ID=%d is not in draft state") % exchange_record.id
            )
        if not exchange_record.direction != "outbound":
            raise exceptions.UserError(
                _("Record ID=%d is not file is not meant to b generated")
                % exchange_record.id
            )
        if exchange_record.exchange_file:
            raise exceptions.UserError(
                _("Record ID=%d already has a file to process!") % exchange_record.id
            )
        output = self._generate_output(exchange_record, **kw)
        if output and store:
            if not isinstance(output, bytes):
                output = output.encode()
            exchange_record.update(
                {
                    "exchange_file": base64.b64encode(output),
                    "edi_exchange_state": "output_pending",
                }
            )
        return tools.pycompat.to_text(output)

    def _generate_output(self, exchange_record, **kw):
        """To be implemented"""
        raise NotImplementedError()
