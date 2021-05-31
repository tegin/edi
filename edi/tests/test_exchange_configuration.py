# Copyright 2021 Creu Blanca
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo_test_helper import FakeModelLoader

from .common import EDIBackendCommonTestCase


class EDIExchangeConfigurationTest(EDIBackendCommonTestCase):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        # Load fake models ->/
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        from .fake_models import EdiExchangeConsumerTest

        cls.loader.update_registry((EdiExchangeConsumerTest,))
        cls.consumer_record = cls.env["edi.exchange.consumer.test"].create(
            {"name": "Test Consumer"}
        )
        cls.exchange_type_out.exchange_filename_pattern = "{record.id}"
        cls.exchange_type_new = cls._create_exchange_type(
            name="Test CSV output",
            code="test_csv_new_output",
            direction="output",
            exchange_file_ext="csv",
            backend_id=False,
            exchange_filename_pattern="{record.ref}-{type.code}-{dt}",
            model_ids=[(4, cls.env["ir.model"]._get_id(cls.consumer_record._name))],
            enable_domain="[]",
            enable_snippet="""result = not   record._has_exchange_record(
            exchange_type.code)""",
        )
        cls.exchange_type_out.write(
            {
                "model_ids": [
                    (4, cls.env["ir.model"]._get_id(cls.consumer_record._name),)
                ],
                "enable_domain": "[]",
                "enable_snippet": """result = not   record._has_exchange_record(
            exchange_type.code, exchange_type.backend_id)""",
            }
        )
        cls.usage = cls.env["edi.exchange.configuration.usage"].create(
            {"name": "demo_usage"}
        )
        cls.configuration = cls.env["edi.exchange.configuration"].create(
            {
                "model": cls.consumer_record._name,
                "res_id": cls.consumer_record.id,
                "backend_id": cls.backend.id,
                "exchange_type_id": cls.exchange_type_new.id,
                "usage_ids": [(6, 0, cls.usage.ids)],
                "advanced_settings_edit": """
extra: 1
list_param:
  - 1
  - 2
""",
            }
        )

    @classmethod
    def tearDownClass(cls):
        cls.loader.restore_registry()
        super().tearDownClass()

    def test_configuration(self):
        exchange_record = self.configuration._generate_exchange_record(
            self.consumer_record
        )
        self.assertTrue(exchange_record)
        self.assertEqual(self.backend, exchange_record.backend_id)
        self.assertEqual(self.exchange_type_new, exchange_record.type_id)
        extra_params = exchange_record.params
        self.assertIn("extra", extra_params)
        self.assertEqual(1, extra_params["extra"])
        self.assertIn("list_param", extra_params)
        self.assertIn(1, extra_params["list_param"])
        self.assertIn(2, extra_params["list_param"])
