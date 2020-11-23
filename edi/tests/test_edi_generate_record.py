# Copyright 2020 ACSONE
# @author: Simone Orsi <simahawk@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import mock

from odoo.tests.common import tagged

from .common import EDIBackendCommonTestCase


@tagged("-at_install", "post_install")
class EDIBackendTestCase(EDIBackendCommonTestCase):
    def test_generate_record_output(self):
        self.exchange_type_out.component_generate = "edi.generate.report"
        company = self.env.company
        vals = {
            "model": company._name,
            "res_id": company.id,
        }
        record = self.backend.create_record("test_csv_output", vals)
        self.assertFalse(record.exchange_file)
        with mock.patch.object(
            type(record.record), "_exchange_record_report_action", create=True,
        ) as patch:
            patch.return_value = self.env.ref("web.action_report_internalpreview")
            self.backend.generate_output(record)

        self.assertTrue(record.exchange_file)
