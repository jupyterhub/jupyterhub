"""JupyterHub version info"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
# version_info updated by running `tbump`
version_info = (5, 2, 0, "", "dev")

# pep 440 version: no dot before beta/rc, but before .dev
# 0.1.0rc1
# 0.1.0a1
# 0.1.0b1.dev
# 0.1.0.dev

__version__ = ".".join(map(str, version_info[:3])) + ".".join(version_info[3:]).rstrip(
    "."
)

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

    # semver: compare major versions only
    if hub_version != singleuser_version:
        from packaging.version import parse

        hub = parse(hub_version)
        singleuser = parse(singleuser_version)
        extra = ""
        do_log = True
        if singleuser.major == hub.major:
            # minor-level mismatch or lower, log difference at debug-level
            # because this should be fine
            log_method = log.debug
        else:
            # log warning-level for more significant mismatch, such as 1.0.0 vs 2.0.0
            key = f'{hub_version}-{singleuser_version}'
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
        log.debug(f"jupyterhub and jupyterhub-singleuser both on version {hub_version}")
