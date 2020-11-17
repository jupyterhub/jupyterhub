# Networking basics

This section will help you with basic proxy and network configuration to:

- set the proxy's IP address and port
- set the proxy's REST API URL
- configure the Hub if the Proxy or Spawners are remote or isolated
- set the `hub_connect_ip` which services will use to communicate with the hub

## Set the Proxy's IP address and port

The Proxy's main IP address setting determines where JupyterHub is available to users.
By default, JupyterHub is configured to be available on all network interfaces
(`''`) on port 8000. *Note*: Use of `'*'` is discouraged for IP configuration;
instead, use of `'0.0.0.0'` is preferred.

Changing the Proxy's main IP address and port can be done with the following
JupyterHub **command line options**:

```bash
jupyterhub --ip=192.168.1.2 --port=443
```

Or by placing the following lines in a **configuration file**,
`jupyterhub_config.py`:

```python
c.JupyterHub.ip = '192.168.1.2'
c.JupyterHub.port = 443
```

Port 443 is used in the examples since 443 is the default port for SSL/HTTPS.

Configuring only the main IP and port of JupyterHub should be sufficient for
most deployments of JupyterHub. However, more customized scenarios may need
additional networking details to be configured.

Note that `c.JupyterHub.ip` and `c.JupyterHub.port` are single values,
not tuples or lists – JupyterHub listens to only a single IP address and
port.

## Set the Proxy's REST API communication URL (optional)

By default, this REST API listens on port 8001 of `localhost` only.
The Hub service talks to the proxy via a REST API on a secondary port. The
API URL can be configured separately and override the default settings.

### Set api_url

The URL to access the API, `c.configurableHTTPProxy.api_url`, is configurable.
An example entry to set the proxy's API URL in `jupyterhub_config.py` is:

```python
c.ConfigurableHTTPProxy.api_url = 'http://10.0.1.4:5432'
```

### proxy_api_ip and proxy_api_port (Deprecated in 0.8)

If running the Proxy separate from the Hub, configure the REST API communication
IP address and port by adding this to the `jupyterhub_config.py` file:

```python
# ideally a private network address
c.JupyterHub.proxy_api_ip = '10.0.1.4'
c.JupyterHub.proxy_api_port = 5432
```

We recommend using the proxy's `api_url` setting instead of the deprecated
settings, `proxy_api_ip` and `proxy_api_port`.

## Configure the Hub if the Proxy or Spawners are remote or isolated

The Hub service listens only on `localhost` (port 8081) by default.
The Hub needs to be accessible from both the proxy and all Spawners.
When spawning local servers, an IP address setting of `localhost` is fine.

If *either* the Proxy *or* (more likely) the Spawners will be remote or
isolated in containers, the Hub must listen on an IP that is accessible.

```python
c.JupyterHub.hub_ip = '10.0.1.4'
c.JupyterHub.hub_port = 54321
```

**Added in 0.8:** The `c.JupyterHub.hub_connect_ip` setting is the ip address or
hostname that other services should use to connect to the Hub. A common
configuration for, e.g. docker, is:

```python
c.JupyterHub.hub_ip = '0.0.0.0'  # listen on all interfaces
c.JupyterHub.hub_connect_ip = '10.0.1.4'  # ip as seen on the docker network. Can also be a hostname.
```

## Adjusting the hub's URL

The hub will most commonly be running on a hostname of its own.  If it
is not – for example, if the hub is being reverse-proxied and being
exposed at a URL such as `https://proxy.example.org/jupyter/` – then
you will need to tell JupyterHub the base URL of the service.  In such
a case, it is both necessary and sufficient to set
`c.JupyterHub.base_url = '/jupyter/'` in the configuration.
