# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import responses
from requests import auth, exceptions

from odoo.tests.common import tagged

from odoo.addons.component.tests.common import SavepointComponentCase


@tagged("-at_install", "post_install")
class CommonWebService(SavepointComponentCase):
    @classmethod
    def _setup_context(cls):
        return dict(
            cls.env.context, tracking_disable=True, test_queue_job_no_delay=True
        )

    @classmethod
    def _setup_env(cls):
        cls.env = cls.env(context=cls._setup_context())

    @classmethod
    def _setup_records(cls):
        pass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_env()
        cls._setup_records()
        # cls._load_module_components(cls, "webservice")


class TestWebService(CommonWebService):
    @classmethod
    def _setup_records(cls):
        super()._setup_records()
        cls.url = "http://localhost.demo.odoo/"
        cls.webservice = cls.env["webservice.backend"].create(
            {
                "name": "WebService",
                "protocol": "http",
                "url": cls.url,
                "content_type": "application/xml",
                "code": "demo_ws",
            }
        )

    def test_web_service_not_found(self):
        with self.assertRaises(exceptions.ConnectionError):
            self.webservice.call("get")

    @responses.activate
    def test_web_service_get_mocked(self):
        responses.add(responses.GET, self.url, body="{}")
        result = self.webservice.call("get")
        self.assertEqual(result, b"{}")
        self.assertEqual(1, len(responses.calls))
        self.assertEqual(
            responses.calls[0].request.headers["Content-Type"], "application/xml"
        )

    @responses.activate
    def test_web_service_post_mocked(self):
        responses.add(responses.POST, self.url, body="{}")
        result = self.webservice.call("post", data="hola")
        self.assertEqual(result, b"{}")
        self.assertEqual(
            responses.calls[0].request.headers["Content-Type"], "application/xml"
        )
        self.assertEqual(responses.calls[0].request.body, "hola")

    @responses.activate
    def test_web_service_put_mocked(self):
        responses.add(responses.PUT, self.url, body="{}")
        result = self.webservice.call("put", data="hola")
        self.assertEqual(result, b"{}")
        self.assertEqual(
            responses.calls[0].request.headers["Content-Type"], "application/xml"
        )
        self.assertEqual(responses.calls[0].request.body, "hola")

    @responses.activate
    def test_web_service_backend_username(self):
        self.webservice.write({"username": "user", "password": "pass"})
        responses.add(responses.GET, self.url, body="{}")
        result = self.webservice.call("get")
        self.assertEqual(result, b"{}")
        self.assertEqual(1, len(responses.calls))
        self.assertEqual(
            responses.calls[0].request.headers["Content-Type"], "application/xml"
        )
        data = auth._basic_auth_str("user", "pass")
        self.assertEqual(responses.calls[0].request.headers["Authorization"], data)

    @responses.activate
    def test_web_service_username(self):
        self.webservice.write({"username": "user", "password": "pass"})
        responses.add(responses.GET, self.url, body="{}")
        result = self.webservice.call("get", auth=("user2", "pass2"))
        self.assertEqual(result, b"{}")
        self.assertEqual(1, len(responses.calls))
        self.assertEqual(
            responses.calls[0].request.headers["Content-Type"], "application/xml"
        )
        data = auth._basic_auth_str("user2", "pass2")
        self.assertEqual(responses.calls[0].request.headers["Authorization"], data)

    @responses.activate
    def test_web_service_headers(self):
        responses.add(responses.GET, self.url, body="{}")
        result = self.webservice.call("get", headers={"demo_header": "HEADER"})
        self.assertEqual(result, b"{}")
        self.assertEqual(1, len(responses.calls))
        self.assertEqual(
            responses.calls[0].request.headers["Content-Type"], "application/xml"
        )
        self.assertEqual(responses.calls[0].request.headers["demo_header"], "HEADER")
