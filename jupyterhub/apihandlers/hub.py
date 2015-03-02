"""API handlers for administering the Hub itself"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import json

from tornado import web
from tornado.ioloop import IOLoop

from ..utils import admin_only
from .base import APIHandler

class ShutdownAPIHandler(APIHandler):
    
    @admin_only
    def post(self):
        """POST /api/shutdown triggers a clean shutdown
        
        POST (JSON) parameters:
        
        - servers: specify whether single-user servers should be terminated
        - proxy: specify whether the proxy should be terminated
        """
        from ..app import JupyterHub
        app = JupyterHub.instance()
        
        data = self.get_json_body()
        if data:
            if 'proxy' in data:
                proxy = data['proxy']
                if proxy not in {True, False}:
                    raise web.HTTPError(400, "proxy must be true or false, got %r" % proxy)
                app.cleanup_proxy = proxy
            if 'servers' in data:
                servers = data['servers']
                if servers not in {True, False}:
                    raise web.HTTPError(400, "servers must be true or false, got %r" % servers)
                app.cleanup_servers = servers
        
        # finish the request
        self.set_status(202)
        self.finish(json.dumps({
            "message": "Shutting down Hub"
        }))
        
        # stop the eventloop, which will trigger cleanup
        loop = IOLoop.current()
        loop.add_callback(loop.stop)


default_handlers = [
    (r"/api/shutdown", ShutdownAPIHandler),
]
