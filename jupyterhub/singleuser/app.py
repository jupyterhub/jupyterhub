"""Make a single-user app based on the environment:

- $JUPYTERHUB_SINGLEUSER_APP, the base Application class, to be wrapped in JupyterHub authentication.
  default: notebook.notebookapp.NotebookApp
- $JUPYTERHUB_SINGLEUSER_PKG, e.g. notebook or jupyter_server.
  Typically inferred from $JUPYTEHUB_SINGLEUSER_APP.
  Package layout must include:
  - base.handlers.JupyterHandler
  - auth.login.LoginHandler
  - auth.logout.LogoutHandler
"""
import os

from traitlets import import_item

from .mixins import make_singleuser_app

JUPYTERHUB_SINGLEUSER_APP = (
    os.environ.get("JUPYTERHUB_SINGLEUSER_APP") or "notebook.notebookapp.NotebookApp"
)
JUPYTERHUB_SINGLEUSER_PKG = os.environ.get("JUPYTERHUB_SINGLEUSER_PKG") or "notebook"

App = import_item(JUPYTERHUB_SINGLEUSER_APP)

JUPYTERHUB_SINGLEUSER_PKG = os.environ.get("JUPYTERHUB_SINGLEUSER_PKG")
if not JUPYTERHUB_SINGLEUSER_PKG:
    # guess notebook or jupyter_server based on App class
    for cls in App.mro():
        pkg = cls.__module__.split(".", 1)[0]
        if pkg in {"notebook", "jupyter_server"}:
            JUPYTERHUB_SINGLEUSER_PKG = pkg
            break
    else:
        raise RuntimeError(
            "Failed to infer JUPYTERHUB_SINGLEUSER_PKG from {}, please set it directly".format(
                JUPYTERHUB_SINGLEUSER_APP
            )
        )

LoginHandler = import_item(pkg + ".auth.login.LoginHandler")
LogoutHandler = import_item(pkg + ".auth.logout.LogoutHandler")
# BaseHandler could be called JupyterHandler or old IPythonHandler
try:
    BaseHandler = import_item(pkg + ".base.handlers.JupyterHandler")
except ImportError:
    BaseHandler = import_item(pkg + ".base.handlers.IPythonHandler")

SingleUserNotebookApp = make_singleuser_app(
    App,
    LoginHandler=LoginHandler,
    LogoutHandler=LogoutHandler,
    BaseHandler=BaseHandler,
)

main = SingleUserNotebookApp.launch_instance
