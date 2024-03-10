"""API handlers for administering the Hub itself"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import sys
## import logging
## from systemd import journal

from psutil import cpu_count, cpu_percent, process_iter, virtual_memory
from psutil import AccessDenied, NoSuchProcess, ZombieProcess

from time import ctime, time
from tornado import web

from .. import orm
from .._version import __version__
from ..scopes import needs_scope
from .base import APIHandler

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


class SysMonAPIHandler(APIHandler):
    cached_data = { "time" : {}, "system" : {}, "ram_rss_mb": {} }
    update_interval = 10
    ndigits = 1
    last_updated = 0

    ## Logging only occurs if someone is actively looking at the graphs
    ## anyway, so we should do not do this.
    ## log = logging.getLogger("jupyter-metrics")
    ## log.addHandler(journal.JournaldLogHandler())
    ## log.setLevel(logging.INFO)


    def get_metrics_per_user(self):
        """Calculate RSS memory, per-user basis in MB, and cpu percent"""
        memory_rss = {"non_jupyter_users": 0, "all_jupyter_users": 0}
        cpu_perc =  {"non_jupyter_users": 0, "all_jupyter_users": 0}

        jupyter_usernames = {}
        for user in self.db.query(orm.User):
            jupyter_usernames[user.name] = 0
            memory_rss[user.name] = 0
            cpu_perc[user.name] = 0

        for proc in process_iter(['pid', 'username', 'memory_info', 'cpu_percent']):
            try:
                username = proc.info['username']
                user_memory_rss = proc.info['memory_info'].rss
                user_cpu_percent = proc.info['cpu_percent']
                if username in jupyter_usernames:
                    memory_rss[username] += user_memory_rss
                    cpu_perc[username] += user_cpu_percent
                    memory_rss["all_jupyter_users"] += user_memory_rss
                    cpu_perc["all_jupyter_users"] += user_cpu_percent
                else:
                    memory_rss["non_jupyter_users"] += user_memory_rss
                    cpu_perc["non_jupyter_users"] += user_cpu_percent

            except (NoSuchProcess, AccessDenied, ZombieProcess):
                pass

        memory_rss["all_processes"] = memory_rss["all_jupyter_users"] + memory_rss["non_jupyter_users"]
        cpu_perc["all_processes"] = cpu_perc["all_jupyter_users"] + cpu_perc["non_jupyter_users"]
        del memory_rss["non_jupyter_users"]
        del cpu_perc["non_jupyter_users"]

        ## Convert Units
        for term in memory_rss:
            memory_rss[term] = round(memory_rss[term] / 1e6,
                                     ndigits=SysMonAPIHandler.ndigits)  ## MB
            cpu_perc[term] = round(cpu_perc[term], ndigits=SysMonAPIHandler.ndigits)

        return {"cpu_percent" : cpu_perc, "memory_rss_mb" : memory_rss}

    def check_xsrf_cookie(self):
        return

    def get(self):
        """GET /api/sysmon returns resource information about the server

        It currently returns cpu and memory usage information as output by psutil.
        The update interval can be set via 'JupyterHub.sysmon_interval' in the config.
        """
        this = SysMonAPIHandler
        conf = self.settings["config"]["JupyterHub"]

        if "sysmon_interval" in conf:
            this.update_interval = conf["sysmon_interval"]

        current_time = time()
        diff_time = current_time - this.last_updated

        if diff_time >= this.update_interval:
            vmem = virtual_memory()
            this.cached_data = {
                "time": {
                    "cached": ctime(),
                    "update_interval": this.update_interval,
                },
                "system": {
                    "ram_free_gb": round(vmem.free / 1e9, ndigits=this.ndigits),
                    "ram_used_gb": round(vmem.used / 1e9, ndigits=this.ndigits),
                    "ram_total_gb": round(vmem.total / 1e9, ndigits=this.ndigits),
                    "ram_usage_percent": round(vmem.percent, ndigits=this.ndigits),
                    "cpu_usage_percent": round(cpu_percent(), ndigits=this.ndigits),
                    "cpu_count": cpu_count(),
                },
                "user" : self.get_metrics_per_user(),
            }
            this.last_updated = current_time
            ###this.log.info(this.cached_data) ## only log new data

        show_data = this.cached_data
        next_update = this.update_interval - diff_time
        if next_update < 0:
            next_update = this.update_interval

        show_data["time"]["next_update"] = round(next_update, ndigits=this.ndigits)
        show_data["time"]["last_update"] = round(diff_time, ndigits=this.ndigits)

        self.finish(json.dumps(show_data))


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
    (r"/api/sysmon", SysMonAPIHandler),
]
