"""Jupyter server extension for testing JupyterHub

Adds a `<base_url>/jupyterhub-test-info` endpoint handler for accessing whatever
state we want to check about the server
"""

import json

from jupyter_server.base.handlers import JupyterHandler
from tornado import web


class JupyterHubTestHandler(JupyterHandler):
    def initialize(self, app):
        self.app = app

    @web.authenticated
    def get(self):
        def _class_str(obj):
            """Given an instance, return the 'module.Class' string"""
            if obj is None:
                return None

            if obj.__class__ is type:
                cls = obj
            else:
                cls = obj.__class__
            return f"{cls.__module__}.{cls.__name__}"

        info = {
            "current_user": self.current_user,
            "config": self.app.config,
            "root_dir": self.contents_manager.root_dir,
            "disable_user_config": getattr(self.app, "disable_user_config", None),
            "settings": self.settings,
            "config_file_paths": self.app.config_file_paths,
        }
        for attr in ("authenticator", "identity_provider"):
            info[attr] = _class_str(getattr(self.app, attr, None))
        self.set_header("content-type", "application/json")
        self.write(json.dumps(info, default=repr))


def _load_jupyter_server_extension(serverapp):
    """
    This function is called when the extension is loaded.
    """
    serverapp.log.warning(f"Loading jupyterhub test extension for {serverapp}")
    handlers = [
        (
            serverapp.base_url + 'jupyterhub-test-info',
            JupyterHubTestHandler,
            {"app": serverapp},
        )
    ]
    serverapp.web_app.add_handlers('.*$', handlers)
