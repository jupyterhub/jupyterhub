"""Service handlers

Currently GET-only, no actions can be taken to modify services.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from ..scopes import needs_scope
from .base import APIHandler


class ServiceListAPIHandler(APIHandler):
    @needs_scope('read:services', 'read:services:name', 'read:roles:services')
    def get(self):
        data = {}
        for name, service in self.services.items():
            model = self.service_model(service)
            if model:
                data[name] = model
        self.write(json.dumps(data))


class ServiceAPIHandler(APIHandler):
    @needs_scope('read:services', 'read:services:name', 'read:roles:services')
    def get(self, service_name):
        service = self.services[service_name]
        self.write(json.dumps(self.service_model(service)))


default_handlers = [
    (r"/api/services", ServiceListAPIHandler),
    (r"/api/services/([^/]+)", ServiceAPIHandler),
]
