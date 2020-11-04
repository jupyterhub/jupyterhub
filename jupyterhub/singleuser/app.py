"""Make a single-user app based on the environment:

- $JUPYTERHUB_SINGLEUSER_APP, the base Application class, to be wrapped in JupyterHub authentication.
  default: notebook.notebookapp.NotebookApp
"""
import os

from traitlets import import_item

from .mixins import make_singleuser_app

JUPYTERHUB_SINGLEUSER_APP = (
    os.environ.get("JUPYTERHUB_SINGLEUSER_APP") or "notebook.notebookapp.NotebookApp"
)

App = import_item(JUPYTERHUB_SINGLEUSER_APP)

SingleUserNotebookApp = make_singleuser_app(App)

main = SingleUserNotebookApp.launch_instance
