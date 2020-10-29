"""JupyterHub version info"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

version_info = (
    1,
    2,
    0,
    # "b1",  # release (b1, rc1, or "" for final or dev)
    # "dev",  # dev or nothing for beta/rc/stable releases
)

# pep 440 version: no dot before beta/rc, but before .dev
# 0.1.0rc1
# 0.1.0a1
# 0.1.0b1.dev
# 0.1.0.dev

__version__ = ".".join(map(str, version_info[:3])) + ".".join(version_info[3:])

# Singleton flag to only log the major/minor mismatch warning once per mismatch combo.
_version_mismatch_warning_logged = {}


def reset_globals():
    """Used to reset globals between test cases."""
    global _version_mismatch_warning_logged
    _version_mismatch_warning_logged = {}


def _check_version(hub_version, singleuser_version, log):
    """Compare Hub and single-user server versions"""
    if not hub_version:
        log.warning(
            "Hub has no version header, which means it is likely < 0.8. Expected %s",
            __version__,
        )
        return

    if not singleuser_version:
        log.warning(
            "Single-user server has no version header, which means it is likely < 0.8. Expected %s",
            __version__,
        )
        return

    # compare minor X.Y versions
    if hub_version != singleuser_version:
        from distutils.version import LooseVersion as V

        hub_major_minor = V(hub_version).version[:2]
        singleuser_major_minor = V(singleuser_version).version[:2]
        extra = ""
        do_log = True
        if singleuser_major_minor == hub_major_minor:
            # patch-level mismatch or lower, log difference at debug-level
            # because this should be fine
            log_method = log.debug
        else:
            # log warning-level for more significant mismatch, such as 0.8 vs 0.9, etc.
            key = '%s-%s' % (hub_version, singleuser_version)
            global _version_mismatch_warning_logged
            if _version_mismatch_warning_logged.get(key):
                do_log = False  # We already logged this warning so don't log it again.
            else:
                log_method = log.warning
                extra = " This could cause failure to authenticate and result in redirect loops!"
                _version_mismatch_warning_logged[key] = True
        if do_log:
            log_method(
                "jupyterhub version %s != jupyterhub-singleuser version %s." + extra,
                hub_version,
                singleuser_version,
            )
    else:
        log.debug(
            "jupyterhub and jupyterhub-singleuser both on version %s" % hub_version
        )
