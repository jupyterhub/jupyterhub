(services-reference)=

# Services

## Definition of a Service

When working with JupyterHub, a **Service** is defined as something (usually a process) that can interact with the Hub's REST API.
A Service may perform a specific action or task.
For example, the following tasks can each be a unique Service:

- shutting down individuals' single user notebook servers that have been idle for some time
- an additional web application which uses the Hub as an OAuth provider to authenticate and authorize user access
- a script run once in a while, which performs any API action
- automating requests to running user servers, such as activity data collection

Two key features help differentiate Services:

- Is the Service **managed** by JupyterHub?
- Does the Service have a web server that should be added to the proxy's table?

Currently, these characteristics distinguish two types of Services:

- A **Hub-Managed Service** which is managed by JupyterHub
- An **Externally-Managed Service** which runs its own web server and
  communicates operation instructions via the Hub's API.

## Properties of a Service

A Service may have the following properties:

- `name: str` - the name of the service
- `url: str (default - None)` - The URL where the service should be running (from the proxy's perspective).
  Typically a localhost URL for Hub-managed services.
  If a url is specified,
  the service will be added to the proxy at `/services/:name`.
- `api_token: str (default - None)` - For Externally-Managed Services,
  you need to specify an API token to perform API requests to the Hub.
  For Hub-managed services, this token is generated at startup,
  and available via `$JUPYTERHUB_API_TOKEN`.
  For OAuth services, this is the client secret.
- `display: bool (default - True)` - When set to true, display a link to the
  service's URL under the 'Services' dropdown in users' hub home page.
  Only has an effect if `url` is also specified.
- `oauth_no_confirm: bool (default - False)` - When set to true,
  skip the OAuth confirmation page when users access this service.
  By default, when users authenticate with a service using JupyterHub,
  they are prompted to confirm that they want to grant that service
  access to their credentials.
  Skipping the confirmation page is useful for admin-managed services that are considered part of the Hub
  and shouldn't need extra prompts for login.
- `oauth_client_id: str (default - 'service-$name')` -
  This never needs to be set, but you can specify a service's OAuth client id.
  It must start with `service-`.
- `oauth_redirect_uri: str (default: '/services/:name/oauth_redirect')` -
  Set the OAuth redirect URI.
  Required if the redirect URI differs from the default or the service is not to be added to the proxy at `/services/:name`
  (i.e. `url` is not set, but there is still a public web service using OAuth).

If a service is also to be managed by the Hub, it has a few extra options:

- `command: (str/Popen list)` - Command for JupyterHub to spawn the service. - Only use this if the service should be a subprocess. - If command is not specified, the Service is assumed to be managed
  externally. - If a command is specified for launching the Service, the Service will
  be started and managed by the Hub.
- `environment: dict` - additional environment variables for the Service.
- `user: str` - the name of a system user to manage the Service.
  If unspecified, run as the same user as the Hub.

## Hub-Managed Services

A **Hub-Managed Service** is started by the Hub, and the Hub is responsible
for the Service's operation. A Hub-Managed Service can only be a local
subprocess of the Hub. The Hub will take care of starting the process and
restart the service if the service stops.

While Hub-Managed Services share some similarities with single-user server Spawners,
there are no plans for Hub-Managed Services to support the same spawning
abstractions as a Spawner.

If you wish to run a Service in a Docker container or other deployment
environments, the Service can be registered as an
**Externally-Managed Service**, as described below.

## Launching a Hub-Managed Service

A Hub-Managed Service is characterized by its specified `command` for launching
the Service. For example, a 'cull idle' notebook server task configured as a
Hub-Managed Service would include:

- the Service name,
- permissions to see when users are active, and to stop servers
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
]

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

(service-env)=

```bash
JUPYTERHUB_SERVICE_NAME:   The name of the service
JUPYTERHUB_API_TOKEN:      API token assigned to the service
JUPYTERHUB_API_URL:        URL for the JupyterHub API (default, http://127.0.0.1:8080/hub/api)
JUPYTERHUB_BASE_URL:       Base URL of the Hub (https://mydomain[:port]/)
JUPYTERHUB_SERVICE_PREFIX: URL path prefix of this service (/services/:service-name/)
JUPYTERHUB_SERVICE_URL:    Local URL where the service is expected to be listening.
                           Only for proxied web services.
JUPYTERHUB_OAUTH_SCOPES:   JSON-serialized list of scopes to use for allowing access to the service
                           (deprecated in 3.0, use JUPYTERHUB_OAUTH_ACCESS_SCOPES).
JUPYTERHUB_OAUTH_ACCESS_SCOPES: JSON-serialized list of scopes to use for allowing access to the service (new in 3.0).
JUPYTERHUB_OAUTH_CLIENT_ALLOWED_SCOPES: JSON-serialized list of scopes that can be requested by the oauth client on behalf of users (new in 3.0).
JUPYTERHUB_PUBLIC_URL: the public URL of the service,
  e.g. `https://jupyterhub.example.org/services/name/`.
  Empty if no public URL is specified (default).
  Will be available if subdomains are configured.
JUPYTERHUB_PUBLIC_HUB_URL: the public URL of JupyterHub as a whole,
  e.g. `https://jupyterhub.example.org/`.
  Empty if no public URL is specified (default).
  Will be available if subdomains are configured.
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

A configuration example of an Externally-Managed Service running its own web
server is:

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

(service-credentials)=

## Service credentials

A service has direct access to the Hub API via its `api_token`.
Exactly what actions the service can take are governed by the service's [role assignments](define-role-target):

```python
c.JupyterHub.services = [
    {
        "name": "user-lister",
        "command": ["python3", "/path/to/user-lister"],
    }
]

c.JupyterHub.load_roles = [
    {
        "name": "list-users",
        "scopes": ["list:users", "read:users"],
        "services": ["user-lister"]
    }
]
```

When a service has a configured URL or explicit `oauth_client_id` or `oauth_redirect_uri`, it can operate as an [OAuth client](explanation:hub-oauth).
When a user visits an oauth-authenticated service,
completion of authentication results in issuing an oauth token.

This token is:

- owned by the authenticated user
- associated with the oauth client of the service
- governed by the service's `oauth_client_allowed_scopes` configuration

This token enables the service to act _on behalf of_ the user.

When an oauthenticated service makes a request to the Hub (or other Hub-authenticated service), it has two credentials available to authenticate the request:

- the service's own `api_token`, which acts _as_ the service,
  and is governed by the service's own role assignments.
- the user's oauth token issued to the service during the oauth flow,
  which acts _as_ the user.

Choosing which one to use depends on "who" should be considered taking the action represented by the request.

A service's own permissions governs how it can act without any involvement of a user.
The service's `oauth_client_allowed_scopes` configuration allows individual users to _delegate_ permission for the service to act on their behalf.
This allows services to have little to no permissions of their own,
but allow users to take actions _via_ the service,
using their own credentials.

An example of such a service would be a web application for instructors,
presenting a dashboard of actions which can be taken for students in their courses.
The service would need no permission to do anything with the JupyterHub API on its own,
but it could employ the user's oauth credentials to list users,
manage student servers, etc.

This service might look like:

```python
c.JupyterHub.services = [
    {
        "name": "grader-dashboard",
        "command": ["python3", "/path/to/grader-dashboard"],
        "url": "http://127.0.0.1:12345",
        "oauth_client_allowed_scopes": [
            "list:users",
            "read:users",
        ]
    }
]

c.JupyterHub.load_roles = [
    {
        "name": "grader",
        "scopes": [
            "list:users!group=class-a",
            "read:users!group=class-a",
            "servers!group=class-a",
            "access:servers!group=class-a",
            "access:services",
        ],
        "groups": ["graders"]
    }
]
```

In this example, the `grader-dashboard` service does not have permission to take any actions with the Hub API on its own because it has not been assigned any role.
But when a grader accesses the service,
the dashboard will have a token with permission to list and read information about any users that the grader can access.
The dashboard will _not_ have permission to do additional things as the grader.

The dashboard will be able to:

- list users in class A (`list:users!group=class-a`)
- read information about users in class A (`read:users!group=class-a`)

The dashboard will _not_ be able to:

- start, stop, or access user servers (`servers`, `access:servers`), even though the grader has this permission (it's not in `oauth_client_allowed_scopes`)
- take any action without the grader granting permission via oauth

## Adding or removing services at runtime

Only externally-managed services can be added at runtime by using JupyterHub’s REST API.

### Add a new service

To add a new service, send a POST request to this endpoint

```
POST /hub/api/services/:servicename
```

**Required scope: `admin:services`**

**Payload**: The payload should contain the definition of the service to be created. The endpoint supports the same properties as externally-managed services defined in the config file.

**Possible responses**

- `201 Created`: The service and related objects are created (and started in case of a Hub-managed one) successfully.
- `400 Bad Request`: The payload is invalid or JupyterHub can not create the service.
- `409 Conflict`: The service with the same name already exists.

### Remove an existing service

To remove an existing service, send a DELETE request to this endpoint

```
DELETE /hub/api/services/:servicename
```

**Required scope: `admin:services`**

**Payload**: `None`

**Possible responses**

- `200 OK`: The service and related objects are removed (and stopped in case of a Hub-managed one) successfully.
- `400 Bad Request`: JupyterHub can not remove the service.
- `404 Not Found`: The requested service does not exist.
- `405 Not Allowed`: The requested service is created from the config file, it can not be removed at runtime.

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

When you run a service that has a URL, it will be accessible under a
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

JupyterHub provides some utilities for using the Hub's authentication
mechanism to govern access to your service.

Requests to all JupyterHub services are made with OAuth tokens.
These can either be requests with a token in the `Authorization` header,
or url parameter `?token=...`,
or browser requests which must complete the OAuth authorization code flow,
which results in a token that should be persisted for future requests
(persistence is up to the service,
but an encrypted cookie confined to the service path is appropriate,
and provided by default).

:::{versionchanged} 2.0
The shared `jupyterhub-services` cookie is removed.
OAuth must be used to authenticate browser requests with services.
:::

JupyterHub includes a reference implementation of Hub authentication that
can be used by services. You may go beyond this reference implementation and
create custom hub-authenticating clients and services. We describe the process
below.

The reference, or base, implementation is the {class}`.HubAuth` class,
which implements the API requests to the Hub that resolve a token to a User model.

There are two levels of authentication with the Hub:

- {class}`.HubAuth` - the most basic authentication,
  for services that should only accept API requests authorized with a token.

- {class}`.HubOAuth` - For services that should use oauth to authenticate with the Hub.
  This should be used for any service that serves pages that should be visited with a browser.

To use HubAuth, you must set the `.api_token` instance variable. This can be
done via the HubAuth constructor, direct assignment to a HubAuth object, or via the
`JUPYTERHUB_API_TOKEN` environment variable. A number of the examples in the
root of the jupyterhub git repository set the `JUPYTERHUB_API_TOKEN` variable
so consider having a look at those for further reading
([cull-idle](https://github.com/jupyterhub/jupyterhub/tree/master/examples/cull-idle),
[external-oauth](https://github.com/jupyterhub/jupyterhub/tree/master/examples/external-oauth),
[service-notebook](https://github.com/jupyterhub/jupyterhub/tree/master/examples/service-notebook)
and [service-whoami](https://github.com/jupyterhub/jupyterhub/tree/master/examples/service-whoami))

Most of the logic for authentication implementation is found in the
{meth}`.HubAuth.user_for_token` methods,
which makes a request of the Hub, and returns:

- None, if no user could be identified, or
- a dict of the following form:

  ```python
  {
    "name": "username",
    "groups": ["list", "of", "groups"],
    "scopes": [
        "access:servers!server=username/",
    ],
  }
  ```

You are then free to use the returned user information to take appropriate
action.

HubAuth also caches the Hub's response for a number of seconds,
configurable by the `cookie_cache_max_age` setting (default: five minutes).

If your service would like to make further requests _on behalf of users_,
it should use the token issued by this OAuth process.
If you are using tornado,
you can access the token authenticating the current request with {meth}`.HubAuth.get_token`.

:::{versionchanged} 2.2

{meth}`.HubAuth.get_token` adds support for retrieving
tokens stored in tornado cookies after the completion of OAuth.
Previously, it only retrieved tokens from URL parameters or the Authorization header.
Passing `get_token(handler, in_cookie=False)` preserves this behavior.
:::

### Flask Example

For example, you have a Flask service that returns information about a user.
JupyterHub's HubAuth class can be used to authenticate requests to the Flask
service. See the `service-whoami-flask` example in the
[JupyterHub GitHub repo](https://github.com/jupyterhub/jupyterhub/tree/HEAD/examples/service-whoami-flask)
for more details.

```{literalinclude} ../../../../jupyterhub/examples/service-whoami-flask/whoami-flask.py
:language: python
```

### Authenticating tornado services with JupyterHub

Since most Jupyter services are written with tornado,
we include a mixin class, {class}`.HubOAuthenticated`,
for quickly authenticating your own tornado services with JupyterHub.

Tornado's {py:func}`~.tornado.web.authenticated` decorator calls a Handler's {py:meth}`~.tornado.web.RequestHandler.get_current_user`
method to identify the user. Mixing in {class}`.HubAuthenticated` defines
{meth}`~.HubAuthenticated.get_current_user` to use HubAuth. If you want to configure the HubAuth
instance beyond the default, you'll want to define an {py:meth}`~.tornado.web.RequestHandler.initialize` method,
such as:

```python
class MyHandler(HubOAuthenticated, web.RequestHandler):

    def initialize(self, hub_auth):
        self.hub_auth = hub_auth

    @web.authenticated
    def get(self):
        ...
```

The HubAuth class will automatically load the desired configuration from the Service
[environment variables](service-env).

:::{versionchanged} 2.0

Access scopes are used to govern access to services.
Prior to 2.0,
sets of users and groups could be used to grant access
by defining `.hub_groups` or `.hub_users` on the authenticated handler.
These are ignored if the 2.0 `.hub_scopes` is defined.
:::

:::{seealso}
{meth}`.HubAuth.check_scopes`
:::

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

```{literalinclude} ../../../../jupyterhub/examples/service-whoami-flask/whoami-flask.py
:language: python
```

We recommend looking at the {class}`.HubOAuth` class implementation for reference,
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
     # groups may be omitted, depending on permissions
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
The default required scopes for access are available from `hub_auth.oauth_scopes` or `$JUPYTERHUB_OAUTH_ACCESS_SCOPES`.

An example of using an Externally-Managed Service and authentication is
in the [nbviewer README][nbviewer example] section on securing the notebook viewer,
and an example of its configuration is found [here](https://github.com/jupyter/nbviewer/blob/ed942b10a52b6259099e2dd687930871dc8aac22/nbviewer/providers/base.py#L95).
nbviewer can also be run as a Hub-Managed Service as described [nbviewer README][nbviewer example]
section on securing the notebook viewer.

[requests]: https://docs.python-requests.org/en/master/
[services_auth]: ../api/services.auth.html
[nbviewer example]: https://github.com/jupyter/nbviewer#securing-the-notebook-viewer
[fastapi example]: https://github.com/jupyterhub/jupyterhub/tree/HEAD/examples/service-fastapi
[fastapi]: https://fastapi.tiangolo.com
[jupyterhub_idle_culler]: https://github.com/jupyterhub/jupyterhub-idle-culler
