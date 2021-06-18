# Services

With version 0.7, JupyterHub adds support for **Services**.

This section provides the following information about Services:

- [Definition of a Service](#definition-of-a-service)
- [Properties of a Service](#properties-of-a-service)
- [Hub-Managed Services](#hub-managed-services)
- [Launching a Hub-Managed Service](#launching-a-hub-managed-service)
- [Externally-Managed Services](#externally-managed-services)
- [Writing your own Services](#writing-your-own-services)
- [Hub Authentication and Services](#hub-authentication-and-services)

## Definition of a Service

When working with JupyterHub, a **Service** is defined as a process that interacts
with the Hub's REST API. A Service may perform a specific
action or task. For example, the following tasks can each be a unique Service:

- shutting down individuals' single user notebook servers that have been idle
  for some time
- registering additional web servers which should use the Hub's authentication
  and be served behind the Hub's proxy.

Two key features help define a Service:

- Is the Service **managed** by JupyterHub?
- Does the Service have a web server that should be added to the proxy's
  table?

Currently, these characteristics distinguish two types of Services:

- A **Hub-Managed Service** which is managed by JupyterHub
- An **Externally-Managed Service** which runs its own web server and
  communicates operation instructions via the Hub's API.

## Properties of a Service

A Service may have the following properties:

- `name: str` - the name of the service
- `admin: bool (default - false)` - whether the service should have
  administrative privileges
- `url: str (default - None)` - The URL where the service is/should be. If a
  url is specified for where the Service runs its own web server,
  the service will be added to the proxy at `/services/:name`
- `api_token: str (default - None)` - For Externally-Managed Services you need to specify
  an API token to perform API requests to the Hub

If a service is also to be managed by the Hub, it has a few extra options:

- `command: (str/Popen list)` - Command for JupyterHub to spawn the service. - Only use this if the service should be a subprocess. - If command is not specified, the Service is assumed to be managed
  externally. - If a command is specified for launching the Service, the Service will
  be started and managed by the Hub.
- `environment: dict` - additional environment variables for the Service.
- `user: str` - the name of a system user to manage the Service. If
  unspecified, run as the same user as the Hub.

## Hub-Managed Services

A **Hub-Managed Service** is started by the Hub, and the Hub is responsible
for the Service's actions. A Hub-Managed Service can only be a local
subprocess of the Hub. The Hub will take care of starting the process and
restarts it if it stops.

While Hub-Managed Services share some similarities with notebook Spawners,
there are no plans for Hub-Managed Services to support the same spawning
abstractions as a notebook Spawner.

If you wish to run a Service in a Docker container or other deployment
environments, the Service can be registered as an
**Externally-Managed Service**, as described below.

## Launching a Hub-Managed Service

A Hub-Managed Service is characterized by its specified `command` for launching
the Service. For example, a 'cull idle' notebook server task configured as a
Hub-Managed Service would include:

- the Service name,
- admin permissions, and
- the `command` to launch the Service which will cull idle servers after a
  timeout interval

This example would be configured as follows in `jupyterhub_config.py`:

```python
c.JupyterHub.load_roles = [
    {
        "name": "idle-culler",
        "scopes": [
            "read:users:activity", # read user last_activity
            "servers", # start and stop servers
            # 'admin:users' # needed if culling idle users as well
        ]
    }

c.JupyterHub.services = [
    {
        'name': 'idle-culler',
        'command': [sys.executable, '-m', 'jupyterhub_idle_culler', '--timeout=3600']
    }
]
```

A Hub-Managed Service may also be configured with additional optional
parameters, which describe the environment needed to start the Service process:

- `environment: dict` - additional environment variables for the Service.
- `user: str` - name of the user to run the server if different from the Hub.
  Requires Hub to be root.
- `cwd: path` directory in which to run the Service, if different from the
  Hub directory.

The Hub will pass the following environment variables to launch the Service:

```bash
JUPYTERHUB_SERVICE_NAME:   The name of the service
JUPYTERHUB_API_TOKEN:      API token assigned to the service
JUPYTERHUB_API_URL:        URL for the JupyterHub API (default, http://127.0.0.1:8080/hub/api)
JUPYTERHUB_BASE_URL:       Base URL of the Hub (https://mydomain[:port]/)
JUPYTERHUB_SERVICE_PREFIX: URL path prefix of this service (/services/:service-name/)
JUPYTERHUB_SERVICE_URL:    Local URL where the service is expected to be listening.
                           Only for proxied web services.
JUPYTERHUB_OAUTH_SCOPES:   JSON-serialized list of scopes to use for allowing access to the service.
```

For the previous 'cull idle' Service example, these environment variables
would be passed to the Service when the Hub starts the 'cull idle' Service:

```bash
JUPYTERHUB_SERVICE_NAME: 'idle-culler'
JUPYTERHUB_API_TOKEN: API token assigned to the service
JUPYTERHUB_API_URL: http://127.0.0.1:8080/hub/api
JUPYTERHUB_BASE_URL: https://mydomain[:port]
JUPYTERHUB_SERVICE_PREFIX: /services/idle-culler/
```

See the GitHub repo for additional information about the [jupyterhub_idle_culler][].

## Externally-Managed Services

You may prefer to use your own service management tools, such as Docker or
systemd, to manage a JupyterHub Service. These **Externally-Managed
Services**, unlike Hub-Managed Services, are not subprocesses of the Hub. You
must tell JupyterHub which API token the Externally-Managed Service is using
to perform its API requests. Each Externally-Managed Service will need a
unique API token, because the Hub authenticates each API request and the API
token is used to identify the originating Service or user.

A configuration example of an Externally-Managed Service with admin access and
running its own web server is:

```python
c.JupyterHub.services = [
    {
        'name': 'my-web-service',
        'url': 'https://10.0.1.1:1984',
        # any secret >8 characters, you'll use api_token to
        # authenticate api requests to the hub from your service
        'api_token': 'super-secret',
    }
]
```

In this case, the `url` field will be passed along to the Service as
`JUPYTERHUB_SERVICE_URL`.

## Writing your own Services

When writing your own services, you have a few decisions to make (in addition
to what your service does!):

1. Does my service need a public URL?
2. Do I want JupyterHub to start/stop the service?
3. Does my service need to authenticate users?

When a Service is managed by JupyterHub, the Hub will pass the necessary
information to the Service via the environment variables described above. A
flexible Service, whether managed by the Hub or not, can make use of these
same environment variables.

When you run a service that has a url, it will be accessible under a
`/services/` prefix, such as `https://myhub.horse/services/my-service/`. For
your service to route proxied requests properly, it must take
`JUPYTERHUB_SERVICE_PREFIX` into account when routing requests. For example, a
web service would normally service its root handler at `'/'`, but the proxied
service would need to serve `JUPYTERHUB_SERVICE_PREFIX`.

Note that `JUPYTERHUB_SERVICE_PREFIX` will contain a trailing slash. This must
be taken into consideration when creating the service routes. If you include an
extra slash you might get unexpected behavior. For example if your service has a
`/foo` endpoint, the route would be `JUPYTERHUB_SERVICE_PREFIX + foo`, and
`/foo/bar` would be `JUPYTERHUB_SERVICE_PREFIX + foo/bar`.

## Hub Authentication and Services

JupyterHub 0.7 introduces some utilities for using the Hub's authentication
mechanism to govern access to your service. When a user logs into JupyterHub,
the Hub sets a **cookie (`jupyterhub-services`)**. The service can use this
cookie to authenticate requests.

JupyterHub ships with a reference implementation of Hub authentication that
can be used by services. You may go beyond this reference implementation and
create custom hub-authenticating clients and services. We describe the process
below.

The reference, or base, implementation is the [`HubAuth`][hubauth] class,
which implements the requests to the Hub.

To use HubAuth, you must set the `.api_token`, either programmatically when constructing the class,
or via the `JUPYTERHUB_API_TOKEN` environment variable.

Most of the logic for authentication implementation is found in the
[`HubAuth.user_for_token`][hubauth.user_for_token]
methods, which makes a request of the Hub, and returns:

- None, if no user could be identified, or
- a dict of the following form:

  ```python
  {
    "name": "username",
    "groups": ["list", "of", "groups"],
    "admin": False, # or True
  }
  ```

You are then free to use the returned user information to take appropriate
action.

HubAuth also caches the Hub's response for a number of seconds,
configurable by the `cookie_cache_max_age` setting (default: five minutes).

### Flask Example

For example, you have a Flask service that returns information about a user.
JupyterHub's HubAuth class can be used to authenticate requests to the Flask
service. See the `service-whoami-flask` example in the
[JupyterHub GitHub repo](https://github.com/jupyterhub/jupyterhub/tree/HEAD/examples/service-whoami-flask)
for more details.

```{literalinclude} ../../../examples/service-whoami-flask/whoami-flask.py
:language: python
```

### Authenticating tornado services with JupyterHub

Since most Jupyter services are written with tornado,
we include a mixin class, [`HubAuthenticated`][hubauthenticated],
for quickly authenticating your own tornado services with JupyterHub.

Tornado's `@web.authenticated` method calls a Handler's `.get_current_user`
method to identify the user. Mixing in `HubAuthenticated` defines
`get_current_user` to use HubAuth. If you want to configure the HubAuth
instance beyond the default, you'll want to define an `initialize` method,
such as:

```python
class MyHandler(HubAuthenticated, web.RequestHandler):
    hub_users = {'inara', 'mal'}

    def initialize(self, hub_auth):
        self.hub_auth = hub_auth

    @web.authenticated
    def get(self):
        ...
```

The HubAuth will automatically load the desired configuration from the Service
environment variables.

If you want to limit user access, you can specify allowed users through either the
`.hub_users` attribute or `.hub_groups`. These are sets that check against the
username and user group list, respectively. If a user matches neither the user
list nor the group list, they will not be allowed access. If both are left
undefined, then any user will be allowed.

### Implementing your own Authentication with JupyterHub

If you don't want to use the reference implementation
(e.g. you find the implementation a poor fit for your Flask app),
you can implement authentication via the Hub yourself.
JupyterHub is a standard OAuth2 provider,
so you can use any OAuth 2 client implementation appropriate for your toolkit.
See the [FastAPI example][] for an example of using JupyterHub as an OAuth provider with [FastAPI][],
without using any code imported from JupyterHub.

On completion of OAuth, you will have an access token for JupyterHub,
which can be used to identify the user and the permissions (scopes)
the user has authorized for your service.

You will only get to this stage if the user has the required `access:services!service=$service-name` scope.

To retrieve the user model for the token, make a request to `GET /hub/api/user` with the token in the Authorization header.
For example, using flask:

```{literalinclude} ../../../examples/service-whoami-flask/whoami-flask.py
:language: python
```

We recommend looking at the [`HubOAuth`][huboauth] class implementation for reference,
and taking note of the following process:

1. retrieve the token from the request.
2. Make an API request `GET /hub/api/user`,
   with the token in the `Authorization` header.

   For example, with [requests][]:

   ```python
   r = requests.get(
       "http://127.0.0.1:8081/hub/api/user",
       headers = {
           'Authorization' : f'token {api_token}',
       },
   )
   r.raise_for_status()
   user = r.json()
   ```

3. On success, the reply will be a JSON model describing the user:

   ```python
   {
     "name": "inara",
     # groups  may be omitted, depending on permissions
     "groups": ["serenity", "guild"],
     # scopes is new in JupyterHub 2.0
     "scopes": [
       "access:services",
       "read:users:name",
       "read:users!user=inara",
       "..."
     ]
   }
   ```

The `scopes` field can be used to manage access.
Note: a user will have access to a service to complete oauth access to the service for the first time.
Individual permissions may be revoked at any later point without revoking the token,
in which case the `scopes` field in this model should be checked on each access.
The default required scopes for access are available from `hub_auth.oauth_scopes` or `$JUPYTERHUB_OAUTH_SCOPES`.

An example of using an Externally-Managed Service and authentication is
in [nbviewer README][nbviewer example] section on securing the notebook viewer,
and an example of its configuration is found [here](https://github.com/jupyter/nbviewer/blob/ed942b10a52b6259099e2dd687930871dc8aac22/nbviewer/providers/base.py#L95).
nbviewer can also be run as a Hub-Managed Service as described [nbviewer README][nbviewer example]
section on securing the notebook viewer.

[requests]: http://docs.python-requests.org/en/master/
[services_auth]: ../api/services.auth.html
[huboauth]: ../api/services.auth.html#jupyterhub.services.auth.HubOAuth
[hubauth.user_for_token]: ../api/services.auth.html#jupyterhub.services.auth.HubAuth.user_for_token
[hubauthenticated]: ../api/services.auth.html#jupyterhub.services.auth.HubAuthenticated
[nbviewer example]: https://github.com/jupyter/nbviewer#securing-the-notebook-viewer
[fastapi example]: https://github.com/jupyterhub/jupyterhub/tree/HEAD/examples/service-fastapi
[fastapi]: https://fastapi.tiangolo.com
[jupyterhub_idle_culler]: https://github.com/jupyterhub/jupyterhub-idle-culler
