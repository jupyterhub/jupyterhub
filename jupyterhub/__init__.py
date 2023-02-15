from ._version import __version__, version_info


def _jupyter_server_extension_points():
    """
    Makes the jupyter_server singleuser extension discoverable.

    Returns a list of dictionaries with metadata describing
    where to find the `_load_jupyter_server_extension` function.

    ref: https://jupyter-server.readthedocs.io/en/latest/developers/extensions.html
    """
    from .singleuser.extension import JupyterHubSingleUser

    return [{"module": "jupyterhub", "app": JupyterHubSingleUser}]


__all__ = ["__version__", "version_info"]
