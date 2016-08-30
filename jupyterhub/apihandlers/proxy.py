"""Proxy handlers"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from tornado import gen, web

from .. import orm
from ..utils import admin_only
from .base import APIHandler

class ProxyAPIHandler(APIHandler):
    
    @admin_only
    @gen.coroutine
    def get(self):
        """GET /api/proxy fetches the routing table
        
        This is the same as fetching the routing table directly from the proxy,
        but without clients needing to maintain separate
        """
        routes = yield self.proxy.get_routes()
        self.write(json.dumps(routes))
    
    @admin_only
    @gen.coroutine
    def post(self):
        """POST checks the proxy to ensure"""
        yield self.proxy.check_routes(self.users, self.services)
        
    
    @admin_only
    @gen.coroutine
    def patch(self):
        """PATCH updates the location of the proxy
        
        Can be used to notify the Hub that a new proxy is in charge
        """
        if not self.request.body:
            raise web.HTTPError(400, "need JSON body")
        
        try:
            model = json.loads(self.request.body.decode('utf8', 'replace'))
        except ValueError:
            raise web.HTTPError(400, "Request body must be JSON dict")
        if not isinstance(model, dict):
            raise web.HTTPError(400, "Request body must be JSON dict")
        
        server = self.proxy.api_server
        if 'ip' in model:
            server.ip = model['ip']
        if 'port' in model:
            server.port = model['port']
        if 'protocol' in model:
            server.proto = model['protocol']
        if 'auth_token' in model:
            self.proxy.auth_token = model['auth_token']
        self.db.commit()
        self.log.info("Updated proxy at %s", server.bind_url)
        yield self.proxy.check_routes(self.users, self.services)
        


default_handlers = [
    (r"/api/proxy", ProxyAPIHandler),
]
