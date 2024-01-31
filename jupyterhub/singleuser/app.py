"""Make a single-user app based on the environment:

- $JUPYTERHUB_SINGLEUSER_APP, the base Application class, to be wrapped in JupyterHub authentication.
  default: jupyter_server.serverapp.ServerApp

.. versionchanged:: 2.0

    Default app changed to launch `jupyter labhub`.
    Use JUPYTERHUB_SINGLEUSER_APP='notebook' for the legacy 'classic' notebook server (requires notebook<7).
"""

import os

from traitlets import import_item

from .mixins import make_singleuser_app

JUPYTERHUB_SINGLEUSER_APP = os.environ.get("JUPYTERHUB_SINGLEUSER_APP", "")

# allow shortcut references
_app_shortcuts = {
    "notebook": "notebook.notebookapp.NotebookApp",
    "jupyter-server": "jupyter_server.serverapp.ServerApp",
    "extension": "jupyter_server.serverapp.ServerApp",
}

JUPYTERHUB_SINGLEUSER_APP = _app_shortcuts.get(
    JUPYTERHUB_SINGLEUSER_APP.replace("_", "-"), JUPYTERHUB_SINGLEUSER_APP
)


if JUPYTERHUB_SINGLEUSER_APP:
    if JUPYTERHUB_SINGLEUSER_APP in {"notebook", _app_shortcuts["notebook"]}:
        # better error for notebook v7, which uses jupyter-server
        # when the legacy notebook server is requested
        try:
            from notebook import __version__
        except ImportError:
            # will raise later
            pass
        else:
            # check if this failed because of notebook v7
            _notebook_major_version = int(__version__.split(".", 1)[0])
            if _notebook_major_version >= 7:
                raise ImportError(
                    f"JUPYTERHUB_SINGLEUSER_APP={JUPYTERHUB_SINGLEUSER_APP} is not valid with notebook>=7 (have notebook=={__version__}).\n"
                    f"Leave $JUPYTERHUB_SINGLEUSER_APP unspecified (or use the default JUPYTERHUB_SINGLEUSER_APP=jupyter-server), "
                    'and set `c.Spawner.default_url = "/tree"` to make notebook v7 the default UI.'
                )
    App = import_item(JUPYTERHUB_SINGLEUSER_APP)
else:
    App = None
    _import_error = None
    for JUPYTERHUB_SINGLEUSER_APP in (
        "jupyter_server.serverapp.ServerApp",
        "notebook.notebookapp.NotebookApp",
    ):
        try:
            App = import_item(JUPYTERHUB_SINGLEUSER_APP)
        except ImportError as e:
            if _import_error is None:
                _import_error = e
            continue
        else:
            break
    if App is None:
        raise _import_error


SingleUserNotebookApp = make_singleuser_app(App)


def main():
    """Launch a jupyterhub single-user server"""
    if not os.environ.get("JUPYTERHUB_SINGLEUSER_APP"):
        # app not specified, launch jupyter-labhub by default,
        # if jupyterlab is recent enough (3.1).
        # This is a minimally extended ServerApp that does:
        # 1. ensure lab extension is enabled, and
        # 2. set default URL to `/lab`
        import re

        _version_pat = re.compile(r"(\d+)\.(\d+)")
        try:
            import jupyterlab
            from jupyterlab.labhubapp import SingleUserLabApp

            m = _version_pat.match(jupyterlab.__version__)
        except Exception:
            m = None

        if m is not None:
            version_tuple = tuple(int(v) for v in m.groups())
            if version_tuple >= (3, 1):
                return SingleUserLabApp.launch_instance()

    return SingleUserNotebookApp.launch_instance()
