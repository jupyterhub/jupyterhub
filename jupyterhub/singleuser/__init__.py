"""JupyterHub single-user server entrypoints

Contains default notebook-app subclass and mixins
"""
import os

from .mixins import HubAuthenticatedHandler, make_singleuser_app

if os.environ.get("JUPYTERHUB_SINGLEUSER_EXTENSION", "") not in ("", "0"):
    # check for conflict in singleuser entrypoint environment variables
    if os.environ.get("JUPYTERHUB_SINGLEUSER_APP", "") not in {
        "",
        "jupyter_server",
        "jupyter-server",
        "extension",
        "jupyter_server.serverapp.ServerApp",
    }:
        ext = os.environ["JUPYTERHUB_SINGLEUSER_EXTENSION"]
        app = os.environ["JUPYTERHUB_SINGLEUSER_APP"]
        raise ValueError(
            f"Cannot use JUPYTERHUB_SINGLEUSER_EXTENSION=1 with JUPYTERHUB_SINGLEUSER_APP={app}."
            " Please pick one or the other."
        )
    _as_extension = True
    from .extension import main
else:
    _as_extension = False
    try:
        from .app import SingleUserNotebookApp, main
    except ImportError:
        # check for Jupyter Server 2.0 ?
        from .extension import main
    else:
        # backward-compatibility
        JupyterHubLoginHandler = SingleUserNotebookApp.login_handler_class
        JupyterHubLogoutHandler = SingleUserNotebookApp.logout_handler_class
        OAuthCallbackHandler = SingleUserNotebookApp.oauth_callback_handler_class


__all__ = [
    "SingleUserNotebookApp",
    "main",
    "HubAuthenticatedHandler",
    "make_singleuser_app",
]
