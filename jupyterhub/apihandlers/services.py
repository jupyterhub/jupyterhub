"""Service handlers

Currently GET-only, no actions can be taken to modify services.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from tornado import web

from ..scopes import Scope, needs_scope
from .base import APIHandler


class ServiceListAPIHandler(APIHandler):
    @needs_scope('list:services')
    def get(self):
        data = {}
        service_scope = self.parsed_scopes['list:services']
        for name, service in self.services.items():
            if service_scope == Scope.ALL or name in service_scope.get("service", {}):
                model = self.service_model(service)
                data[name] = model
        self.write(json.dumps(data))


class ServiceAPIHandler(APIHandler):
    @needs_scope('read:services', 'read:services:name', 'read:roles:services')
    def get(self, service_name):
        service = self.services[service_name]
        self.write(json.dumps(self.service_model(service)))

    @needs_scope('admin:services')
    def post(self, service_name: str):
        data = self.get_json_body()
        service = self.find_service(service_name)

        if service is not None:
            raise web.HTTPError(409, f"Service {service_name} already exists")

        if not data or not isinstance(data, dict):
            raise web.HTTPError(400, "Invalid service data")

        data['name'] = service_name
        self._check_service_model(data)
        self.service_from_spec(data)
        self.db.commit()
        service = self.find_service(service_name)
        self.write(json.dumps(self.service_model(service)))
        self.set_status(201)


default_handlers = [
    (r"/api/services", ServiceListAPIHandler),
    (r"/api/services/([^/]+)", ServiceAPIHandler),
]
