(howto:upgrading-v6)=

# Upgrading to JupyterHub 6

This document describes considerations specific to the JupyterHub 6 upgrade.
For general upgrading tips, see the [docs on upgrading jupyterhub](upgrading).

You can see the [changelog](changelog) for more detailed information.

## Python version

JupyterHub 6 requires Python 3.10.
Make sure you have at least Python 3.10 in your user and hub environments before upgrading.

## Database upgrades

JupyterHub 6 includes a database schema upgrade,
so you should backup your database and run `jupyterhub upgrade-db` after upgrading and before starting JupyterHub.

## Named server restrictions

Prior to JupyterHub 6 there were almost no restrictions on the naming of named servers.
Core JupyterHub components correctly handled these, but names with unusual characters caused problems for some extensions, or when interacting with external components.

JupyterHub 6 imposes strict limits on the naming of named servers:

- Between 1 and 30 characters
- Consists of lowercase ASCII letters, digits, and single hyphens (`-`)
- Must start with a lowercase letter
- Must end with a lowercase letter or digit

A new field `display_name` means users can still provide an arbitrary name, separate from the server name used in APIs, URLs, etc.

### Web interface

Users can name a named server as normal- this will be used as the `display_name`.
If this doesn't comply with the above restrictions a safe server name will be automatically derived by stripping disallowed characters, truncating, etc, as needed.
The server name is used in labels, URLs, etc.

### API

API clients that create named servers must provide a name that complies with the above restrictions.
They can optionally provide a user-facing `display_name` in the JSON body.

### Migrating old named servers

A new `c.JupyterHub.allow_existing_invalid_named_servers` property controls how named servers created prior to JupyterHub 6 are handled.

JupyterHub can automatically migrate servers, but this is **not safe to run unless your spawner keeps track of all external resources** such as storage volumes/paths.
For example, if you currently mount the filesystem path `/data/USERNAME/INVALID-SERVERNAME` into the JupyterHub singleuser server and the servername is automatically migrated to `NEW-SERVERNAME`, when the server is started it will mount `/data/USERNAME/NEW-SERVERNAME` instead of the original path.

If this is the case we recommend you:

- create a new named server
- copy the data from the old path to the new path
- delete the old named server

#### Automatic migration

To automatically migrate non-compliant named servers when JupyterHub starts set

```python
c.JupyterHub.allow_existing_invalid_named_servers = "autorename"
```

If a server has to be migrated its `display_name` will be set to the current server name, and a new compliant server name will be generated.

If a server with a non-compliant name is already running when the hub is restarted (e.g. if `c.JupyterHub.cleanup_servers = False`)
it will not be migrated; ensure the server is shutdown before the hub is next restarted.

#### Default behaviour

The default

```python
c.JupyterHub.allow_existing_invalid_named_servers = "allow-start"
```

allows named servers with non-compliant names to be started, stopped, and deleted.
Use this if you are unable to migrate servers.

#### Deletion only

```python
c.JupyterHub.allow_existing_invalid_named_servers = "allow-delete"
```

allows named servers with non-compliant names to be stopped and deleted.
This is to support migration of named servers which is unsafe to do with a running server.

There is no option to create named servers with non-compliant names.

:::{warning}
Support for non-compliant names will be completely dropped in JupyterHub 7, i.e. it will be impossible to start those servers.
:::

## Passing parameters to spawners (`spawner.user_options`)

If parameters are passed to a spawner using URL query parameters in a GET request they should be prefixed with `opt-`.
This ensures they won't clash with parameters used by JupyterHub.

Passing parameters without the `opt-` prefix will continue to work in most cases, with these exceptions:

- If you use the `display_name` parameter this is now used by JupyterHub and is removed from the options passed to the spawner.
  You must use the new format `opt-display_name` instead.
- If you have a parameter beginning with `opt-`, e.g. `opt-a`, this will be converted to `a`.
  You must pass this parameter as `opt-opt-a` instead.
- You can't mix the old and new style of passing parameters.
  If any parameter is passed using the `opt-` prefix all parameters must, others will be ignored.
- Other parameters may be used by JupyterHub in future releases.
  These will not be treated as a breaking change.

For example, instead of calling `GET /spawn?key=value&opt-image=datascience` use
`GET /spawn?opt-key=value&opt-opt-image=datascience`.
This will result in `{"key": "value", "opt-image", "datascience"}`

A similar change is made when specifying options via `POST /api/users/:username/servers/:servername`.
Prior to JupyterHub 6, the whole JSON body was passed as `user_options`, while JupyterHub 6 moves this to a `user_options` key:

```json
// POST /api/users/chee/servers/xlzl
{
  "display_name": "XL-ZL",
  "user_options": {
    "quibble": true
  }
}
```

For backward-compatibility, the full body will still be passed as `user_options`, as long as neither the `user_options` nor `display_name` key is defined.

## statsd metrics removed

JupyterHub had not updated its statsd metrics in a long time, and they have been removed in 6.0.
If you want to continue monitoring JupyterHub metrics, you can switch to the much more widely used Prometheus [metrics](#monitoring).

## aiohttp used for internal communication

Prior to 6.0, JupyterHub used Tornado's [](inv:tornado:py:class#*.AsyncHTTPClient) to make internal HTTP requests
(API requests from user server to the Hub, checks that user servers are available at their designated URL, etc.).
In most cases, for performance reasons, JupyterHub would use the implementation backed by pycurl.
This has been traded for [aiohttp] in JupyterHub 6.
Hopefully, this should have no noticeable affect on deployments, but if you encounter issues,
such as an increase in timeouts spawning servers under load,
you can configure aiohttp via [](#JupyterHubHTTPClient) configuration.

[aiohttp]: https://docs.aiohttp.org

## New server endpoints

There are new server endpoints, especially useful for named servers.
You can now GET information about a single server:

```
GET /hub/api/users/:name/servers/:name
```

which returns the model for just that server
(previously only retrievable from the full user model with all servers at `GET /hub/api/users/:name`)

```
PUT /hub/api/users/:name/servers/:name
```

lets you create a new named server. If a server with that name already exists, it will fail with 409.

```
PATCH /hub/api/users/:name/servers/:name
```

lets you modify a server (such as its display name or `user_options`) _without starting it_.

For more details, check out the [REST API](#jupyterhub-rest-API).

## Unix sockets

JupyterHub and configurable-http-proxy now fully support using Unix domain sockets for internal communication,
including between singleuser servers and the hub.
Configuration and URLs must have the form:

```
http+unix://{socket_path}
```

where `{socket_path}` is the **url-encoded** path of the socket.

For example, to use unix sockets for the configurable-http-proxy and Hub:

```python
# CHP api socket must be accessible to Hub (/srv/juptyerhub/proxy-api.sock)
c.ConfigurableHTTPProxy.api_url = "http+unix://%2Fsrv%2Fjupyterhub%2Fproxy-api.sock"
# CHP public URL must be accessible to reverse proxy (nginx, traefik, etc.): /srv/jupyterhub/chp-public.sock
c.JupyterHub.bind_url = "http+unix://%2Fsrv%2Fjupyterhub%2Fproxy-public.sock"
# Hub API socket must be accessible to all users, proxy: /var/run/jupyterhub/hub.sock
c.JupyterHub.hub_bind_url = "http+unix://%2Fvar%2Frun%2Fjupyterhub%2Fhub.sock"
```

For single-user servers, Spawners must be configured to listen on a unix socket and return an `http+unix://` URL.
This will require a custom Spawner, at this point.

## New scopes

JupyterHub has added two mechanisms to improve

- A new `start:servers` scope, which allows you to grant tokens, applications, or users permission to _start_ specific servers, but not create, access, or stop them.
- A new [](#JupyterHub.extra_user_scopes) option to _add_ scopes to the default user role,
  without needing to _redefine_ it via [](#JupyterHub.load_roles)

## User info

Authenticators may now return a [`user_info`](#authenticator-user-info) dictionary,
containing information to populate things like the JupyterLab collaboration UI
(display name, avatar, etc.).

## PKCE

JupyterHub 6 adds Proof Key for Code Exchange ([PKCE]) to its internal OAuth implementation.
This should be invisible to users, but provides improved security to the internal OAuth mechanism.

For backward-compatibility, if clients do not send PKCE code challenges, JupyterHub will not require a code verifier to complete OAuth.
Strict PKCE enforcement can be enabled by setting:

```python
c.JupyterHub.oauth_require_pkce = True
```

Setting this will prevent any oauth client that does not send PKCE arguments (such as those using OAuth implementations from JupyterHub 5 or before) from completing OAuth.
Any client that does implement PKCE is fully backward compatible with all versions of JupyterHub,
as unrecognized arguments are required to be ignored in OAuth.

[PKCE]: https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce

## SpawnExceptions

In order to allow deployments to better separate spawn failures due to _errors_ (timeouts, unexpected problems) from spawn failures due to _rejections_ (e.g. improper inputs, capacity limits), a new [](#SpawnException) class is defined.
Raising a SpawnException should never result in tracebacks being logged, and should be distinguishable from errors in spawn failure metrics, by having `status=failure` where errors will have `status=error`.

```{seealso}
[](#spawn-errors)
```

### Backward compatibility

Custom Spawners that wish to use this functionality while supporting older JupyterHub versions can get close to the same behavior
by raising a [](inv:tornado:py:exception#*.web.HTTPError):

```python
try:
    from jupyterhub.spawner import SpawnException
except ImportError:
    from tornado.web import HTTPError
    class SpawnException(HTTPError):
        def __init__(
            self, message, *, reason, log_message="", message_html="", status_code=400
        ):
            self.jupyterhub_message = message
            if message_html:
                self.jupyterhub_html_message = message_html

            super().__init__(status_code, log_message or message, reason=reason)
```
