# `cull-idle` Example

The `cull_idle_servers.py` file provides a script to cull and shut down idle
single-user notebook servers. This script is used when `cull-idle` is run as
a Service or when it is run manually as a standalone script.


## Configure `cull-idle` to run as a Hub-Managed Service

In `jupyterhub_config.py`, add the following dictionary for the `cull-idle`
Service to the `c.JupyterHub.services` list:

```python
c.JupyterHub.services = [
    {
        'name': 'cull-idle',
        'admin': True,
        'command': [sys.executable, 'cull_idle_servers.py', '--timeout=3600'],
    }
]
```

where:

- `'admin': True` indicates that the Service has 'admin' permissions, and
- `'command'` indicates that the Service will be managed by the Hub.

## Run `cull-idle` manually as a standalone script

This will run `cull-idle` manually. `cull-idle` can be run as a standalone
script anywhere with access to the Hub, and will periodically check for idle
servers and shut them down via the Hub's REST API. In order to shutdown the
servers, the token given to cull-idle must have admin privileges.

Generate an API token and store it in the `JUPYTERHUB_API_TOKEN` environment
variable. Run `cull_idle_servers.py` manually. 

```bash
    export JUPYTERHUB_API_TOKEN=$(jupyterhub token)
    python3 cull_idle_servers.py [--timeout=900] [--url=http://127.0.0.1:8081/hub/api]
```
