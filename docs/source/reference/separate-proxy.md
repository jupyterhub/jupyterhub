# Running proxy separately from the hub


## Background

The thing which users directly connect to is the proxy, by default
`configurable-http-proxy`.  The proxy either redirects users to the
hub (for login and managing servers), or to their own single-user
servers.  Thus, as long as the proxy stays running, access to existing
servers continues, even if the hub itself restarts or goes down.

When you first configure the hub, you may not even realize this
because the proxy is automatically managed by the hub.  This is great
for getting started and even most use, but everytime you restart the
hub, all user connections also get restarted.  But it's also simple to
run the proxy as a service separate from the hub, so that you are free
to reconfigure the hub while only interrupting users who are currently
actively starting the hub.

The default JupyterHub proxy is
[configurable-http-proxy](https://github.com/jupyterhub/configurable-http-proxy),
and that page has some docs.  If you are using a different proxy, such
as Traefik, these instructions are probably not relevant to you.


## Configuration options

`c.JupyterHub.cleanup_servers = False` should be set, which tells the
hub to not stop servers when the hub restarts (this is useful even if
you don't run the proxy separately).

`c.ConfigurableHTTPProxy.should_start = False` should be set, which
tells the hub that the proxy should not be started (because you start
it yourself).

`c.ConfigurableHTTPProxy.auth_token = "CONFIGPROXY_AUTH_TOKEN"` should be set to a
token for authenticating communication with the proxy.

`c.ConfigurableHTTPProxy.api_url = 'http://localhost:8001'` should be
set to the URL which the hub uses to connect *to the proxy's API*.


## Proxy configuration

You need to configure a service to start the proxy.  An example
command line for this is `configurable-http-proxy --ip=127.0.0.1
--port=8000 --api-ip=127.0.0.1 --api-port=8001
--default-target=http://localhost:8081
--error-target=http://localhost:8081/hub/error`.  (Details for how to
do this is out of scope for this tutorial - for example it might be a
systemd service on within another docker cotainer).  The proxy has no
configuration files, all configuration is via the command line and
environment variables.

`--api-ip` and `--api-port` (which tells the proxy where to listen) should match the hub's `ConfigurableHTTPProxy.api_url`.

`--ip`, `-port`, and other options configure the *user* connections to the proxy.

`--default-target` and `--error-target` should point to the hub, and used when users navigate to the proxy originally.

You must define the environment variable `CONFIGPROXY_AUTH_TOKEN` to
match the token given to `c.ConfigurableHTTPProxy.auth_token`.

You should check the [configurable-http-proxy
options](https://github.com/jupyterhub/configurable-http-proxy) to see
what other options are needed, for example SSL options.  Note that
these are configured in the hub if the hub is starting the proxy - you
need to move the options to here.


## Docker image

You can use [jupyterhub configurable-http-proxy docker
image](https://hub.docker.com/r/jupyterhub/configurable-http-proxy/)
to run the proxy.


## See also

* [jupyterhub configurable-http-proxy](https://github.com/jupyterhub/configurable-http-proxy)
