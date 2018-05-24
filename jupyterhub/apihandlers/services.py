"""Service handlers

Currently GET-only, no actions can be taken to modify services.
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from tornado import web

from .. import orm
from ..utils import admin_only
from .base import APIHandler

def service_model(service):
    """Produce the model for a service"""
    return {
        'name': service.name,
        'admin': service.admin,
        'url': service.url,
        'prefix': service.server.base_url if service.server else '',
        'command': service.command,
        'pid': service.proc.pid if service.proc else 0,
        'info': service.info
    }

class ServiceListAPIHandler(APIHandler):
    @admin_only
    def get(self):
        data = {name: service_model(service) for name, service in self.services.items()}
        self.write(json.dumps(data))


def admin_or_self(method):
    """Decorator for restricting access to either the target service or admin"""
    def decorated_method(self, name):
        current = self.get_current_user()
        if current is None:
            raise web.HTTPError(403)
        if not current.admin:
            # not admin, maybe self
            if not isinstance(current, orm.Service):
                raise web.HTTPError(403)
            if current.name != name:
                raise web.HTTPError(403)
        # raise 404 if not found
        if name not in self.services:
            raise web.HTTPError(404)
        return method(self, name)
    return decorated_method

class ServiceAPIHandler(APIHandler):

    @admin_or_self
    def get(self, name):
        service = self.services[name]
        self.write(json.dumps(service_model(service)))


default_handlers = [
    (r"/api/services", ServiceListAPIHandler),
    (r"/api/services/([^/]+)", ServiceAPIHandler),
]
