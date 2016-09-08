# `cull-idle` Example

The `cull_idle_servers.py` file provides a script to cull and shut down idle
single-user notebook servers. This script is used when `cull-idle` is run as
a Service or when it is run manually.


## Configure `cull-idle` to run as a Managed Service

In `jupyterhub_config.py`, add the following dictionary for the `cull-idle`
Service to the `c.JupyterHub.services` list:

```python
c.JupyterHub.services = [
    {
        'name': 'cull-idle',
        'admin': True,
        'command': 'python cull_idle_servers.py --timeout=3600'.split(),
    }
]
```

where `'admin': True` indicates this is a Managed Service and `command` is
used by the Hub to launch the `cull-idle` Service.


## Run `cull-idle` manually (not as a JupyterHub Service)

This will run `cull-idle` manually. It needs to be done each time by a hub
admin to run `cull-idle` to shut down idle single-user notebook servers. The
admin only needs to run the script on the hub and not the individual
single-user notebook servers.

Generate an API token and store it in the `JUPYTERHUB_API_TOKEN` environment
variable. Run `cull_idle_servers.py` manually. 

```bash
    export JUPYTERHUB_API_TOKEN=`jupyterhub token`
    python cull_idle_servers.py [--timeout=900] [--url=http://127.0.0.1:8081/hub/api]
```
