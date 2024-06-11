(explanation:singleuser)=

# The JupyterHub single-user server

When a user logs into JupyterHub, they get a 'server', which we usually call the **single-user server**, because it's a server that's meant for a single JupyterHub user.
Each JupyterHub user gets a different one (or more than one!).

A single-user server is a process running somewhere that is:

1. accessible over http[s],
2. authenticated via JupyterHub using OAuth 2.0,
3. started by a [Spawner](spawners), and
4. 'owned' by a single JupyterHub user

## The single-user server command

The Spawner's default single-user server startup command, `jupyterhub-singleuser`, launches `jupyter-server`, the same program used when you run `jupyter lab` on your laptop.
(_It can also launch the legacy `jupyter-notebook` server_).
That's why JupyterHub looks familiar to folks who are already using Jupyter at home or elsewhere.
It's the same!
`jupyterhub-singleuser` _customizes_ that program to change (approximately) one thing: **authenticate requests with JupyterHub**.

(singleuser-auth)=

## Single-user server authentication

Implementation-wise, JupyterHub single-user servers are a special-case of {ref}`services-reference`
and as such use the same (OAuth) authentication mechanism (more on OAuth in JupyterHub at [](oauth)).
This is primarily implemented in the {class}`~.HubOAuth` class.

This code resides in `jupyterhub.singleuser` subpackage of JupyterHub.
The main task of this code is to:

1. resolve a JupyterHub token to a JupyterHub user (authenticate)
2. check permissions (`access:servers`) for the token to make sure the request should be allowed (authorize)
3. if not authorized, begin the OAuth process with a redirect to the Hub
4. after login, store OAuth tokens in a cookie only used by this single-user server
5. implement logout to clear the cookie

Most of this is implemented in the {class}`~.HubOAuth` class. `jupyterhub.singleuser` is responsible for _adapting_ the base Jupyter Server to use HubOAuth for these tasks.

### JupyterHub authentication extension

By default, `jupyter-server` uses its own cookie to authenticate.
If that cookie is not present, the server redirects you a login page and asks you to enter a password or token.

Jupyter Server 2.0 introduces two new _APIs_ for customizing authentication: the [IdentityProvider](inv:jupyter-server#jupyter_server.auth.IdentityProvider) and the [Authorizer](inv:jupyter-server#jupyter_server.auth.Authorizer).
More information can be found in the [Jupyter Server documentation](https://jupyter-server.readthedocs.io).

JupyterHub implements these APIs in `jupyterhub.singleuser.extension`.

The IdentityProvider is responsible for _authenticating_ requests.
In JupyterHub, that means extracting OAuth tokens from the request and resolving them to a JupyterHub user.

The Authorizer is a _separate_ API for _authorizing_ actions on particular resources.
Because the JupyterHub IdentityProvider only allows _authenticating_ users who already have the necessary `access:servers` permission to access the server, the default Authorizer only contains a redundant check for this same permission, and ignores the resource inputs.
However, specifying a _custom_ Authorizer allows for granular permissions, such as read-only access to subsets of a shared server.

### JupyterHub authentication via subclass

Prior to Jupyter Server 2 (i.e. Jupyter Server 1.x or the legacy `jupyter-notebook` server), JupyterHub authentication is applied via _subclass_.
Originally a subclass of `NotebookApp`,
this approach works with both `jupyter-server` and `jupyter-notebook`.
Instead of using the extension mechanisms above,
the server application is _subclassed_. This worked well in the `jupyter-notebook` days,
but doesn't fit well with Jupyter Server's extension-based architecture.

### Selecting jupyterhub-singleuser implementation

Using the JupyterHub singleuser-server extension is the default behavior of JupyterHub 4 and Jupyter Server 2, otherwise the subclass approach is taken.

You can opt-out of the extension by setting the environment variable `JUPYTERHUB_SINGLEUSER_EXTENSION=0`:

```python
c.Spawner.environment.update(
    {
        "JUPYTERHUB_SINGLEUSER_EXTENSION": "0",
    }
)
```

The subclass approach will also be taken if you've opted to use the classic notebook server with:

```
JUPYTERHUB_SINGLEUSER_APP=notebook
```

which was introduced in JupyterHub 2.

## Other customizations

`jupyterhub-singleuser` makes other small customizations to how the single-user server behaves:

1. logs activity on the single-user server, used in [idle-culling](https://github.com/jupyterhub/jupyterhub-idle-culler).
2. disables some features that don't make sense in JupyterHub (trash, retrying ports)
3. loading options such as URLs and SSL configuration from the environment
4. customize logging for consistency with JupyterHub logs

## Running a single-user server that's not `jupyterhub-singleuser`

By default, `jupyterhub-singleuser` is the same `jupyter-server` used by JupyterLab, Jupyter notebook (>= 7), etc.
But technically, all JupyterHub cares about is that it is:

1. an http server at the prescribed URL, accessible from the Hub and proxy, and
2. authenticated via [OAuth](oauth) with the Hub (it doesn't even have to do this, if you want to do your own authentication, as is done in BinderHub)

which means that you can customize JupyterHub to launch _any_ web application that meets these criteria, by following the specifications in {ref}`services-reference`.

Most of the time, though, it's easier to use [jupyter-server-proxy](https://jupyter-server-proxy.readthedocs.io) if you want to launch additional web applications in JupyterHub.
