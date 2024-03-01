"""API handlers for administering the Hub itself"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import sys

from tornado import web

from .._version import __version__
from ..scopes import needs_scope
from .base import APIHandler

from psutil import virtual_memory, cpu_count, cpu_percent
from time import time, ctime

class ShutdownAPIHandler(APIHandler):
    @needs_scope('shutdown')
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
                    raise web.HTTPError(
                        400, "proxy must be true or false, got %r" % proxy
                    )
                app.cleanup_proxy = proxy
            if 'servers' in data:
                servers = data['servers']
                if servers not in {True, False}:
                    raise web.HTTPError(
                        400, "servers must be true or false, got %r" % servers
                    )
                app.cleanup_servers = servers

        # finish the request
        self.set_status(202)
        self.finish(json.dumps({"message": "Shutting down Hub"}))

        # instruct the app to stop, which will trigger cleanup
        app.stop()


class RootAPIHandler(APIHandler):
    def check_xsrf_cookie(self):
        return

    def get(self):
        """GET /api/ returns info about the Hub and its API.

        It is not an authenticated endpoint
        For now, it just returns the version of JupyterHub itself.
        """
        data = {'version': __version__}
        self.finish(json.dumps(data))


class ResourcesAPIHandler(APIHandler):
    last_updated = 0
    cached_data = {}
    seconds_interval = 10
    
    def check_xsrf_cookie(self):
        return

    def get(self):
        """GET /api/resources returns resource information about the server

          It currently returns cpu and memory usage information without authentication
        """
        current_time = time()
        if current_time - ResourcesAPIHandler.last_updated >= ResourcesAPIHandler.seconds_interval:
            ResourcesAPIHandler.cached_data = {
                "last_updated": ctime(),
                "seconds_interval": ResourcesAPIHandler.seconds_interval,
                ##"virtual_memory" : dict(virtual_memory()._asdict()),                
                "ram_free_gb": virtual_memory().free / 1e9,
                "ram_used_gb" : virtual_memory().used / 1e9,
                "ram_total_gb" : virtual_memory().total / 1e9,
                "ram_free_percent": round(100 * virtual_memory().available / virtual_memory().total),
                "ram_used_percent": virtual_memory().percent,
                "cpu_usage_percent": round(cpu_percent()),
                "cpu_count" : cpu_count()
            }
            ResourcesAPIHandler.last_updated = current_time            
            
        self.finish(json.dumps(ResourcesAPIHandler.cached_data))


class InfoAPIHandler(APIHandler):
    @needs_scope('read:hub')
    def get(self):
        """GET /api/info returns detailed info about the Hub and its API.

        Currently, it returns information on the python version, spawner and authenticator.
        Since this information might be sensitive, it is an authenticated endpoint
        """

        def _class_info(typ):
            """info about a class (Spawner or Authenticator)"""
            info = {'class': f'{typ.__module__}.{typ.__name__}'}
            pkg = typ.__module__.split('.')[0]
            try:
                version = sys.modules[pkg].__version__
            except (KeyError, AttributeError):
                version = 'unknown'
            info['version'] = version
            return info

        data = {
            'version': __version__,
            'python': sys.version,
            'sys_executable': sys.executable,
            'spawner': _class_info(self.settings['spawner_class']),
            'authenticator': _class_info(self.authenticator.__class__),
        }
        self.finish(json.dumps(data))


default_handlers = [
    (r"/api/shutdown", ShutdownAPIHandler),
    (r"/api/?", RootAPIHandler),
    (r"/api/info", InfoAPIHandler),
    (r"/api/resources", ResourcesAPIHandler),
]
