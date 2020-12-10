# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests

from odoo.addons.component.core import AbstractComponent, Component


class BaseWebServiceAdapter(AbstractComponent):
    _name = "base.webservice.adapter"
    _collection = "webservice.backend"
    _webservice_protocol = False
    _usage = "webservice.request"

    @classmethod
    def _component_match(cls, work, usage=None, model_name=None, **kw):
        """Override to customize match.
        Registry lookup filtered by usage and model_name when landing here.
        Now, narrow match to `_match_attrs` attributes.
        """
        return kw.get("webservice_protocol") in (None, cls._webservice_protocol)


class BaseRestRequestsAdapter(Component):
    _name = "base.requests"
    _webservice_protocol = "http"
    _inherit = "base.webservice.adapter"

    def _request(self, method, **kwargs):
        new_kwargs = kwargs.copy()
        new_kwargs.update(
            {"auth": self._get_auth(**kwargs), "headers": self._get_headers(**kwargs)}
        )
        request = requests.request(
            method, self.collection.url.format(**kwargs), **new_kwargs
        )
        request.raise_for_status()
        return request.content

    def get(self, **kwargs):
        return self._request("get", **kwargs)

    def post(self, **kwargs):
        return self._request("post", **kwargs)

    def put(self, **kwargs):
        return self._request("put", **kwargs)

    def _get_auth(self, auth=False, **kwargs):
        if auth:
            return auth
        if self.collection.username and self.collection.password:
            return self.collection.username, self.collection.password
        return None

    def _get_headers(self, content_type=False, headers=False, **kwargs):
        result = {
            "Content-Type": content_type or self.collection.content_type,
        }
        if isinstance(headers, dict):
            result.update(headers)
        return result
