"""
Utility methods for use in jupyterhub_config.py and dynamic subconfigs.

Methods here can be imported by extraConfig in values.yaml
"""
from collections import Mapping
from functools import lru_cache
import os

import yaml

# memoize so we only load config once
@lru_cache()
def _load_config():
    """Load the Helm chart configuration used to render the Helm templates of
    the chart from a mounted k8s Secret, and merge in values from an optionally
    mounted secret (hub.existingSecret)."""

    cfg = {}
    for source in ("secret/values.yaml", "existing-secret/values.yaml"):
        path = f"/usr/local/etc/jupyterhub/{source}"
        if os.path.exists(path):
            print(f"Loading {path}")
            with open(path) as f:
                values = yaml.safe_load(f)
            cfg = _merge_dictionaries(cfg, values)
        else:
            print(f"No config at {path}")
    return cfg


@lru_cache()
def _get_config_value(key):
    """Load value from the k8s ConfigMap given a key."""

    path = f"/usr/local/etc/jupyterhub/config/{key}"
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    else:
        raise Exception(f"{path} not found!")


@lru_cache()
def get_secret_value(key, default="never-explicitly-set"):
    """Load value from the user managed k8s Secret or the default k8s Secret
    given a key."""

    for source in ("existing-secret", "secret"):
        path = f"/usr/local/etc/jupyterhub/{source}/{key}"
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
    if default != "never-explicitly-set":
        return default
    raise Exception(f"{key} not found in either k8s Secret!")


def get_name(name):
    """Returns the fullname of a resource given its short name"""
    return _get_config_value(name)


def get_name_env(name, suffix=""):
    """Returns the fullname of a resource given its short name along with a
    suffix, converted to uppercase with dashes replaced with underscores. This
    is useful to reference named services associated environment variables, such
    as PROXY_PUBLIC_SERVICE_PORT."""
    env_key = _get_config_value(name) + suffix
    env_key = env_key.upper().replace("-", "_")
    return os.environ[env_key]


def _merge_dictionaries(a, b):
    """Merge two dictionaries recursively.

    Simplified From https://stackoverflow.com/a/7205107
    """
    merged = a.copy()
    for key in b:
        if key in a:
            if isinstance(a[key], Mapping) and isinstance(b[key], Mapping):
                merged[key] = _merge_dictionaries(a[key], b[key])
            else:
                merged[key] = b[key]
        else:
            merged[key] = b[key]
    return merged


def get_config(key, default=None):
    """
    Find a config item of a given name & return it

    Parses everything as YAML, so lists and dicts are available too

    get_config("a.b.c") returns config['a']['b']['c']
    """
    value = _load_config()
    # resolve path in yaml
    for level in key.split("."):
        if not isinstance(value, dict):
            # a parent is a scalar or null,
            # can't resolve full path
            return default
        if level not in value:
            return default
        else:
            value = value[level]
    return value


def set_config_if_not_none(cparent, name, key):
    """
    Find a config item of a given name, set the corresponding Jupyter
    configuration item if not None
    """
    data = get_config(key)
    if data is not None:
        setattr(cparent, name, data)
