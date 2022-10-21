# Interpreting common log messages

When debugging errors and outages, looking at the logs emitted by
JupyterHub is very helpful. This document intends to describe some common
log messages, what they mean and what are the most common causes that generated them, as well as some possible ways to fix them.

## Failing suspected API request to not-running server

### Example

Your logs might be littered with lines that look scary

```
[W 2022-03-10 17:25:19.774 JupyterHub base:1349] Failing suspected API request to not-running server: /hub/user/<user-name>/api/metrics/v1
```

### Cause

This likely means that the user's server has stopped running but they
still have a browser tab open. For example, you might have 3 tabs open and you shut
the server down via one.
Another possible reason could be that you closed your laptop and the server was culled for inactivity, then reopened the laptop!
However, the client-side code (JupyterLab, Classic Notebook, etc) doesn't interpret the shut-down server and continues to make some API requests.

JupyterHub's architecture means that the proxy routes all requests that
don't go to a running user server to the hub process itself. The hub
process then explicitly returns a failure response, so the client knows
that the server is not running anymore. This is used by JupyterLab to
inform the user that the server is not running anymore, and provide an option
to restart it.

Most commonly, you'll see this in reference to the `/api/metrics/v1`
URL, used by [jupyter-resource-usage](https://github.com/jupyter-server/jupyter-resource-usage).

### Actions you can take

This log message is benign, and there is usually no action for you to take.

## JupyterHub Singleuser Version mismatch

### Example

```
 jupyterhub version 1.5.0 != jupyterhub-singleuser version 1.3.0. This could cause failure to authenticate and result in redirect loops!
```

### Cause

JupyterHub requires the `jupyterhub` python package installed inside the image or
environment, the user server starts in. This message indicates that the version of
the `jupyterhub` package installed inside the user image or environment is not
the same as the JupyterHub server's version itself. This is not necessarily always a
problem - some version drift is mostly acceptable, and the only two known cases of
breakage are across the 0.7 and 2.0 version releases. In those cases, issues pop
up immediately after upgrading your version of JupyterHub, so **always check the JupyterHub
changelog before upgrading!**. The primary problems this _could_ cause are:

1. Infinite redirect loops after the user server starts
2. Missing expected environment variables in the user server once it starts
3. Failure for the started user server to authenticate with the JupyterHub server -
   note that this is _not_ the same as _user authentication_ failing!

However, for the most part, unless you are seeing these specific issues, the log
message should be counted as a warning to get the `jupyterhub` package versions
aligned, rather than as an indicator of an existing problem.

### Actions you can take

Upgrade the version of the `jupyterhub` package in your user environment or image
so that it matches the version of JupyterHub running your JupyterHub server! If you
are using the [zero-to-jupyterhub](https://z2jh.jupyter.org) helm chart, you can find the appropriate
version of the `jupyterhub` package to install in your user image [here](https://jupyterhub.github.io/helm-chart/)
