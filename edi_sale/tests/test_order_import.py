# Copyright 2018 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import base64
import json

import mock

from odoo.addons.component.tests.common import SavepointComponentRegistryCase


class TestOrderImport(SavepointComponentRegistryCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls._load_module_components(cls, "edi")
        cls._load_module_components(cls, "edi_sale")
        cls.edi_backend = cls.env.ref("edi_sale.backend")
        cls.edi_backend_type = cls.env.ref("edi_sale.backend_type")
        cls.partner = cls.env.ref("base.res_partner_2")
        cls.env["edi.exchange.type"].create(
            {
                "backend_type_id": cls.edi_backend_type.id,
                "name": "SO Exchange Tye",
                "code": "sale.order.import.demo",
                "direction": "input",
            }
        )
        cls.product = cls.env["product.product"].create({"name": "DEMO PRODUCT"})
        cls.parsed_order = {
            "partner": {"email": "deco.addict82@example.com"},
            "date": "2018-08-14",
            "order_ref": "TEST1242",
            "lines": [
                {
                    "product": {"code": "FURN_8888"},
                    "qty": 2,
                    "uom": {"unece_code": "C62"},
                    "price_unit": 12.42,
                }
            ],
            "chatter_msg": [],
            "doc_type": "rfq",
        }
        cls.delivery_product = cls.env.ref("product.product_delivery_02")

    def test_order_import(self):
        so_import = self.env["sale.order.import"].create(
            {"order_file": b"1234", "order_filename": "filename.xml"}
        )
        exchange_record = self.edi_backend.create_record(
            "sale.order.import.demo",
            {
                "model": so_import._name,
                "res_id": so_import.id,
                "edi_exchange_state": "input_received",
                "exchange_file": base64.b64encode(
                    json.dumps(self.parsed_order).encode("utf-8")
                ),
            },
        )
        so_import.edi_exchange_record_id = exchange_record
        order_action = so_import.edi_create_order_button()
        order = self.env[order_action["res_model"]].browse(order_action["res_id"])
        self.assertEqual(order, exchange_record.record)
        self.assertEquals(order.client_order_ref, self.parsed_order["order_ref"])
        self.assertEquals(
            order.order_line[0].product_id.default_code,
            self.parsed_order["lines"][0]["product"]["code"],
        )
        self.assertEquals(int(order.order_line[0].product_uom_qty), 2)
        parsed_order_up = {
            "partner": {"email": "deco.addict82@example.com"},
            "date": "2018-08-14",
            "order_ref": "TEST1242",
            "lines": [
                {
                    "product": {"code": "FURN_8888"},
                    "qty": 3,
                    "uom": {"unece_code": "C62"},
                    "price_unit": 12.42,
                },
                {
                    "product": {"code": "FURN_9999"},
                    "qty": 1,
                    "uom": {"unece_code": "C62"},
                    "price_unit": 1.42,
                },
            ],
            "chatter_msg": [],
            "doc_type": "rfq",
        }

        so_import_update = self.env["sale.order.import"].create(
            {
                "order_file": b"1234",
                "order_filename": "filename.xml",
                "sale_id": order.id,
            }
        )
        exchange_record_update = self.edi_backend.create_record(
            "sale.order.import.demo",
            {
                "model": so_import_update._name,
                "res_id": so_import_update.id,
                "edi_exchange_state": "input_received",
                "exchange_file": base64.b64encode(
                    json.dumps(parsed_order_up).encode("utf-8")
                ),
            },
        )
        so_import_update.edi_exchange_record_id = exchange_record_update
        order_action = so_import_update.update_order_button()
        order = self.env[order_action["res_model"]].browse(order_action["res_id"])
        self.assertEqual(order, exchange_record_update.record)
        self.assertEquals(len(order.order_line), 2)
        self.assertEquals(int(order.order_line[0].product_uom_qty), 3)

    def test_import_pdf(self):
        so_import = self.env["sale.order.import"].create(
            {"order_file": b"1234", "order_filename": "filename.pdf"}
        )
        bdio = self.env["business.document.import"]
        component = self.edi_backend._find_component(
            ["edi.input.receive.sale_order_import.sale.order.import.xml"]
        )
        with mock.patch.object(type(bdio), "get_xml_files_from_pdf") as mck:
            mck.return_value = {"test.xml": b"1234"}
            with mock.patch.object(type(component), "_receive") as mck_receive:
                mck_receive.return_value = self.parsed_order
                result = so_import.import_order_button()
                mck_receive.assert_called()
            mck.assert_called()
        self.assertEqual(result["res_model"], "sale.order")
        order = self.env[result["res_model"]].browse(result["res_id"])
        self.assertEquals(order.client_order_ref, self.parsed_order["order_ref"])
        self.assertEquals(
            order.order_line[0].product_id.default_code,
            self.parsed_order["lines"][0]["product"]["code"],
        )
        self.assertEquals(int(order.order_line[0].product_uom_qty), 2)

    def test_import_with_so(self):
        new_order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "client_order_ref": "TEST1242",
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "price_unit": 30})
                ],
            }
        )
        self.assertTrue(
            new_order.order_line.filtered(lambda r: r.product_id == self.product)
        )
        so_import = self.env["sale.order.import"].create(
            {"order_file": b"1234", "order_filename": "filename.pdf"}
        )
        bdio = self.env["business.document.import"]
        component = self.edi_backend._find_component(
            ["edi.input.receive.sale_order_import.sale.order.import.xml"]
        )
        with mock.patch.object(type(bdio), "get_xml_files_from_pdf") as mck:
            mck.return_value = {"test.xml": b"1234"}
            with mock.patch.object(type(component), "_receive") as mck_receive:
                mck_receive.return_value = self.parsed_order
                result = so_import.import_order_button()
                mck_receive.assert_called()
            mck.assert_called()
        self.assertNotEqual(result["res_model"], "sale.order")
        object_result = self.env[result["res_model"]].browse(result["res_id"])
        self.assertEqual(object_result, so_import)
        self.assertEqual(so_import.state, "update")
        self.assertEqual(so_import.sale_id, new_order)
        so_import.price_source = "pricelist"
        self.delivery_product.lst_price = 60
        order_action = so_import.update_order_button()
        order = self.env[order_action["res_model"]].browse(order_action["res_id"])
        self.assertEqual(order, new_order)
        self.assertEqual(order.client_order_ref, self.parsed_order["order_ref"])
        self.assertFalse(
            new_order.order_line.filtered(lambda r: r.product_id == self.product)
        )
        self.assertEqual(
            order.order_line[0].product_id.default_code,
            self.parsed_order["lines"][0]["product"]["code"],
        )
        self.assertEqual(int(order.order_line[0].product_uom_qty), 2)
        self.assertEqual(order.order_line[0].price_unit, 60)
