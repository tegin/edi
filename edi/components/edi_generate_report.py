from odoo.addons.component.core import Component


class EdiGenerateReport(Component):
    _name = "edi.generate.report"
    _usage = "edi.generate.report"
    _collection = "edi.backend"

    def generate(self, exchange_report):
        action = exchange_report.record._exchange_record_report_action()
        return action.render(exchange_report.record.ids, {})[0]
