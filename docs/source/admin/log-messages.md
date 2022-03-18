# Common log messages emitted by JupyterHub

When debugging errors and outages, looking at the logs emitted by
JupyterHub is very helpful. This document tries to document some common
log messages, and what they mean.

## Failing suspected API request to not-running server

### Example

Your logs might be littered with lines that might look slightly scary

```
[W 2022-03-10 17:25:19.774 JupyterHub base:1349] Failing suspected API request to not-running server: /hub/user/<user-name>/api/metrics/v1
```

### Most likely cause

This likely means is that the user's server has stopped running but they
still have a browser tab open. For example, you might have 3 tabs open, and shut
your server down via one. Or you closed your laptop, your server was
culled for inactivity, and then you reopen your laptop again! The
client side code (JupyterLab, Classic Notebook, etc) does not know
yet that the server is dead, and continues to make some API requests.
JupyterHub's architecture means that the proxy routes all requests that
don't go to a running user server to the hub process itself. The hub
process then explicitly returns a failure response, so the client knows
that the server is not running anymore. This is used by JupyterLab to
tell you your server is not running anymore, and offer you the option
to let you restart it.

Most commonly, you'll see this in reference to the `/api/metrics/v1`
URL, used by [jupyter-resource-usage](https://github.com/jupyter-server/jupyter-resource-usage).

### Actions you can take

This log message is benign, and there is usually no action for you to take.
