"""
Disable user-controlled config for single-user servers

Applies patches to prevent loading configuration from the user's home directory.

Only used when launching a single-user server with disable_user_config=True.

This is where we still have some monkeypatches,
because we want to prevent loading configuration from user directories,
and `jupyter_core` functions don't allow that.

Due to extensions, we aren't able to apply patches in one place on the ServerApp,
we have to insert the patches at the lowest-level
on function objects themselves,
to ensure we modify calls to e.g. `jupyter_core.jupyter_path`
that may have been imported already!

We should perhaps ask for the necessary hooks to modify this in jupyter_core,
rather than keeing these monkey patches around.
"""

import os
from pathlib import Path

from jupyter_core import paths


def _is_relative_to(path, prefix):
    """
    Backport Path.is_relative_to for Python < 3.9

    added in Python 3.9
    """
    if hasattr(path, "is_relative_to"):
        # Python >= 3.9
        return path.is_relative_to(prefix)
    else:
        return path == prefix or prefix in path.parents


def _exclude_home(path_list):
    """Filter out any entries in a path list that are in my home directory.

    Used to disable per-user configuration.
    """
    # resolve paths before comparison
    # so we do the right thing when $HOME is a symlink
    home = Path.home().resolve()
    for path in path_list:
        if not _is_relative_to(Path(path).resolve(), home):
            yield path


# record patches
_original_jupyter_paths = None
_jupyter_paths_without_home = None


def _disable_user_config(serverapp):
    """
    disable user-controlled sources of configuration
    by excluding directories in their home from paths.

    This _does not_ disable frontend config,
    such as UI settings persistence.

    1. Python config file paths
    2. Search paths for extensions, etc.
    3. import path
    """
    original_jupyter_path = paths.jupyter_path()
    jupyter_path_without_home = list(_exclude_home(original_jupyter_path))

    # config_file_paths is a property without a setter
    # can't override on the instance
    default_config_file_paths = serverapp.config_file_paths
    config_file_paths = list(_exclude_home(default_config_file_paths))
    serverapp.__class__.config_file_paths = property(
        lambda self: config_file_paths,
    )
    # verify patch applied
    assert serverapp.config_file_paths == config_file_paths

    # patch jupyter_path to exclude $HOME
    global \
        _original_jupyter_paths, \
        _jupyter_paths_without_home, \
        _original_jupyter_config_dir
    _original_jupyter_paths = paths.jupyter_path()
    _jupyter_paths_without_home = list(_exclude_home(_original_jupyter_paths))

    def get_jupyter_path_without_home(*subdirs):
        # reimport because of our `__code__` patch
        # affects what is resolved as the parent namespace
        from jupyterhub.singleuser._disable_user_config import (
            _jupyter_paths_without_home,
        )

        paths = list(_jupyter_paths_without_home)
        if subdirs:
            paths = [os.path.join(p, *subdirs) for p in paths]
        return paths

    # patch `jupyter_path.__code__` to ensure all callers are patched,
    # even if they've already imported
    # this affects e.g. nbclassic.nbextension_paths
    paths.jupyter_path.__code__ = get_jupyter_path_without_home.__code__

    # same thing for config_dir,
    # which applies to some things like ExtensionApp config paths
    # and nbclassic.static_custom_path

    # allows explicit override if $JUPYTER_CONFIG_DIR is set
    # or config dir is otherwise not in $HOME

    if not os.getenv("JUPYTER_CONFIG_DIR") and not list(
        _exclude_home([paths.jupyter_config_dir()])
    ):
        # patch specifically Application.config_dir
        # this affects ServerApp and ExtensionApp,
        # but does not affect JupyterLab's user-settings, etc.
        # patching the traitlet directly affects all instances,
        # already-created or future
        from jupyter_core.application import JupyterApp

        def get_env_config_dir(obj, cls=None):
            return paths.ENV_CONFIG_PATH[0]

        JupyterApp.config_dir.get = get_env_config_dir

    # record disabled state on app object
    serverapp.disable_user_config = True
