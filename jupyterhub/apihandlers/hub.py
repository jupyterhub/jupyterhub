"""API handlers for administering the Hub itself"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from tornado import web
from tornado.ioloop import IOLoop

from ..utils import admin_only
from .base import APIHandler

class ShutdownAPIHandler(APIHandler):
    
    @admin_only
    def post(self):
        """POST /api/shutdown triggers a clean shutdown
        
        URL parameters:
        
        - servers: specify whether single-user servers should be terminated
        - proxy: specify whether the proxy should be terminated
        """
        from ..app import JupyterHub
        app = JupyterHub.instance()
        proxy = self.get_argument('proxy', '').lower()
        if proxy == 'false':
            app.cleanup_proxy = False
        elif proxy == 'true':
            app.cleanup_proxy = True
        elif proxy:
            raise web.HTTPError(400, "proxy must be true or false, got %r" % proxy)
        servers = self.get_argument('servers', '').lower()
        if servers == 'false':
            app.cleanup_servers = False
        elif servers == 'true':
            app.cleanup_servers = True
        elif servers:
            raise web.HTTPError(400, "servers must be true or false, got %r" % servers)
        
        # finish the request
        self.set_status(202)
        self.finish()
        
        # stop the eventloop, which will trigger cleanup
        loop = IOLoop.current()
        loop.add_callback(loop.stop)


default_handlers = [
    (r"/api/shutdown", ShutdownAPIHandler),
]
