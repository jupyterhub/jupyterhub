from ._version import __version__, version_info


def _jupyter_server_extension_points():
    from .singleuser.extension import JupyterHubSingleUser

    return [{"module": "jupyterhub", "app": JupyterHubSingleUser}]


__all__ = ["__version__", "version_info"]
