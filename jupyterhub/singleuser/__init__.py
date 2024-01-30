"""JupyterHub single-user server entrypoints

Contains default notebook-app subclass and mixins

Defaults to:

- Jupyter server extension with Jupyter Server >=2
- Subclass with Jupyter Server <2 or clasic notebook

Application subclass can be controlled with environment variables:

- JUPYTERHUB_SINGLEUSER_EXTENSION=1 to opt-in to the extension (requires Jupyter Server 2)
- JUPYTERHUB_SINGLEUSER_APP=notebook (or jupyter-server) to opt-in
"""

import os

from .mixins import HubAuthenticatedHandler, make_singleuser_app

_as_extension = False
_extension_env = os.environ.get("JUPYTERHUB_SINGLEUSER_EXTENSION", "")
_app_env = os.environ.get("JUPYTERHUB_SINGLEUSER_APP", "")

if not _extension_env:
    # extension env not set, check app env
    if not _app_env or 'jupyter_server' in _app_env.replace("-", "_"):
        # no app env set or using jupyter-server, this is the default branch
        # default behavior:
        # - extension, if jupyter server 2
        # - older subclass app, otherwise
        try:
            import jupyter_server

            _server_major = int(jupyter_server.__version__.split(".", 1)[0])
        except Exception:
            # don't have jupyter-server, assume classic notebook
            _as_extension = False
        else:
            # default to extension if jupyter-server >=2
            _as_extension = _server_major >= 2

    elif _app_env == "extension":
        _as_extension = True
    else:
        # app env set and not to jupyter-server, that opts out of extension
        _as_extension = False
elif _extension_env == "0":
    _as_extension = False
else:
    # extension env set to anything non-empty other than '0' enables the extension
    _as_extension = True

if _as_extension:
    # check for conflict in singleuser entrypoint environment variables
    if _app_env not in {
        "",
        "jupyter_server",
        "jupyter-server",
        "extension",
        "jupyter_server.serverapp.ServerApp",
    }:
        raise ValueError(
            f"Cannot use JUPYTERHUB_SINGLEUSER_EXTENSION={_extension_env} with JUPYTERHUB_SINGLEUSER_APP={_app_env}."
            " Please pick one or the other."
        )
    from .extension import main
else:
    from .app import SingleUserNotebookApp, main

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
