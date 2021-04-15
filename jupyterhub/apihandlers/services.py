"""Service handlers

Currently GET-only, no actions can be taken to modify services.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json

from tornado import web

from .. import orm
from ..scopes import needs_scope
from .base import APIHandler


def service_model(service):
    """Produce the model for a service"""
    return {
        'name': service.name,
        'admin': service.admin,
        'roles': [r.name for r in service.roles],
        'url': service.url,
        'prefix': service.server.base_url if service.server else '',
        'command': service.command,
        'pid': service.proc.pid if service.proc else 0,
        'info': service.info,
        'display': service.display,
    }


class ServiceListAPIHandler(APIHandler):
    @needs_scope('read:services')
    def get(self):
        scope_filter = self.get_scope_filter('read:services')
        data = {
            name: service_model(service)
            for name, service in self.services.items()
            if scope_filter(service, kind='service')
        }
        self.write(json.dumps(data))


class ServiceAPIHandler(APIHandler):
    @needs_scope('read:services')
    def get(self, service_name):
        service = self.services[service_name]
        self.write(json.dumps(service_model(service)))


default_handlers = [
    (r"/api/services", ServiceListAPIHandler),
    (r"/api/services/([^/]+)", ServiceAPIHandler),
]
