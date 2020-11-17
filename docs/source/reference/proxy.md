# Writing a custom Proxy implementation

JupyterHub 0.8 introduced the ability to write a custom implementation of the
proxy. This enables deployments with different needs than the default proxy,
configurable-http-proxy (CHP). CHP is a single-process nodejs proxy that the
Hub manages by default as a subprocess (it can be run externally, as well, and
typically is in production deployments).

The upside to CHP, and why we use it by default, is that it's easy to install
and run (if you have nodejs, you are set!). The downsides are that it's a
single process and does not support any persistence of the routing table. So
if the proxy process dies, your whole JupyterHub instance is inaccessible
until the Hub notices, restarts the proxy, and restores the routing table. For
deployments that want to avoid such a single point of failure, or leverage
existing proxy infrastructure in their chosen deployment (such as Kubernetes
ingress objects), the Proxy API provides a way to do that.

In general, for a proxy to be usable by JupyterHub, it must:

1. support websockets without prior knowledge of the URL where websockets may
   occur
2. support trie-based routing (i.e. allow different routes on `/foo` and
   `/foo/bar` and route based on specificity)
3. adding or removing a route should not cause existing connections to drop

Optionally, if the JupyterHub deployment is to use host-based routing,
the Proxy must additionally support routing based on the Host of the request.

## Subclassing Proxy

To start, any Proxy implementation should subclass the base Proxy class,
as is done with custom Spawners and Authenticators.

```python
from jupyterhub.proxy import Proxy

class MyProxy(Proxy):
    """My Proxy implementation"""
    ...
```

## Starting and stopping the proxy

If your proxy should be launched when the Hub starts, you must define how
to start and stop your proxy:

```python
class MyProxy(Proxy):
    ...
    async def start(self):
        """Start the proxy"""

    async def stop(self):
        """Stop the proxy"""
```

These methods **may** be  coroutines.

`c.Proxy.should_start` is a configurable flag that determines whether the
Hub should call these methods when the Hub itself starts and stops.

## Encryption

When using `internal_ssl` to encrypt traffic behind the proxy, at minimum,
your `Proxy` will need client ssl certificates which the `Hub` must be made
aware of. These can be generated with the command `jupyterhub --generate-certs`
which will write them to the `internal_certs_location` in folders named
`proxy_api` and `proxy_client`. Alternatively, these can be provided to the
hub via the `jupyterhub_config.py` file by providing a `dict` of named paths
to the `external_authorities` option. The hub will include all certificates
provided in that `dict` in the trust bundle utilized by all internal
components.

### Purely external proxies

Probably most custom proxies will be externally managed,
such as Kubernetes ingress-based implementations.
In this case, you do not need to define `start` and `stop`.
To disable the methods, you can define `should_start = False` at the class level:

```python
class MyProxy(Proxy):
    should_start = False
```

## Routes

At its most basic, a Proxy implementation defines a mechanism to add, remove,
and retrieve routes. A proxy that implements these three methods is complete.
Each of these methods **may** be a coroutine.

**Definition:** routespec

A routespec, which will appear in these methods, is a string describing a
route to be proxied, such as `/user/name/`. A routespec will:

1. always end with `/`
2. always start with `/` if it is a path-based route `/proxy/path/`
3. precede the leading `/` with a host for host-based routing, e.g.
   `host.tld/proxy/path/`

### Adding a route

When adding a route, JupyterHub may pass a JSON-serializable dict as a `data`
argument that should be attached to the proxy route. When that route is
retrieved, the `data` argument should be returned as well. If your  proxy
implementation doesn't support storing data attached to routes, then your
Python wrapper may have to handle storing the `data` piece itself, e.g in a
simple file or database.

```python
async def add_route(self, routespec, target, data):
    """Proxy `routespec` to `target`.

    Store `data` associated with the routespec
    for retrieval later.
    """
```

Adding a route for a user looks like this:

```python
await proxy.add_route('/user/pgeorgiou/', 'http://127.0.0.1:1227',
                {'user': 'pgeorgiou'})
```

### Removing routes

`delete_route()` is given a routespec to delete. If there is no such route,
`delete_route` should still succeed, but a warning may be issued.

```python
async def delete_route(self, routespec):
    """Delete the route"""
```

### Retrieving routes

For retrieval, you only *need* to implement a single method that retrieves all
routes. The return value for this function should be a dictionary, keyed by
`routespect`, of dicts whose keys are the same three arguments passed to
`add_route` (`routespec`, `target`, `data`)

```python
async def get_all_routes(self):
    """Return all routes, keyed by routespec"""
```

```python
{
  '/proxy/path/': {
    'routespec': '/proxy/path/',
    'target': 'http://...',
    'data': {},
  },
}
```

## Note on activity tracking

JupyterHub can track activity of users, for use in services such as culling
idle servers. As of JupyterHub 0.8, this activity tracking is the
responsibility of the proxy. If your proxy implementation can track activity
to endpoints, it may add a `last_activity` key to the `data` of routes
retrieved in `.get_all_routes()`. If present, the value of `last_activity`
should be an [ISO8601](https://en.wikipedia.org/wiki/ISO_8601) UTC date
string:

```python
{
  '/user/pgeorgiou/': {
    'routespec': '/user/pgeorgiou/',
    'target': 'http://127.0.0.1:1227',
    'data': {
      'user': 'pgeourgiou',
      'last_activity': '2017-10-03T10:33:49.570Z',
    },
  },
}
```

If the proxy does not track activity, then only activity to the Hub itself is
tracked, and services such as cull-idle will not work.

Now that `notebook-5.0` tracks activity internally, we can retrieve activity
information from the single-user servers instead, removing the need to track
activity in the proxy. But this is not yet implemented in JupyterHub 0.8.0.

### Registering custom Proxies via entry points

As of JupyterHub 1.0, custom proxy implementations can register themselves via
the `jupyterhub.proxies` entry point metadata.
To do this, in your `setup.py` add:

```python
setup(
  ...
  entry_points={
    'jupyterhub.proxies': [
        'mything = mypackage:MyProxy',
    ],
  },
)
```

If you have added this metadata to your package,
users can select your proxy with the configuration:

```python
c.JupyterHub.proxy_class = 'mything'
```

instead of the full

```python
c.JupyterHub.proxy_class = 'mypackage:MyProxy'
```

previously required.
Additionally, configurable attributes for your proxy will
appear in jupyterhub help output and auto-generated configuration files
via `jupyterhub --generate-config`.
