# User-initiated sharing

This example contains a jupyterhub configuration and sample notebooks demonstrating user-initiated sharing from within a JupyterLab session.

What _admins_ need to do is enable sharing:

```python
c.JupyterHub.load_roles = [
    {
        "name": "user",
        "scopes": ["self", "shares!user"],
    }
]
```

## Getting a token with sharing permission

Users can always issue themselves tokens with the desired permissions.
But for a deployment, it's likely that you want to grant sharing permission to something,
be it a service or some part of the single-user application.

There are two ways to do this in a single-user session,
and for convenience, this example includes both.
In most real deployments, it will only make sense to do one or the other.

### Sharing via JupyterLab extension

If you have a JupyterLab javascript sharing extension or server extension,
sharing permissions should be granted to the oauth tokens used to visit the single-user server.
These permissions can be specified:

```python
# OAuth token should have sharing permissions,
# so JupyterLab javascript can manage shares
c.Spawner.oauth_client_allowed_scopes = ["access:servers!server", "shares!server"]
```

The notebook `share-jupyterlab.ipynb` contains a few javascript snippets which will use the JupyterLab configuration to make API requests to JupyterHub from javascript in order to grant access.

This workflow _should_ be handled by a proper JupyterLab extension,
but this notebook of javascript snippets serves as a proof of concept for what is required to build such an extension.

## Sharing via API token

These same permissions can also be granted to the server token itself,
which is available as $JUPYTERHUB_API_TOKEN in the server,
as well as terminals and notebooks.

```python
# grant $JUPYTERHUB_API_TOKEN sharing permissions
# so that _python_ code can manage shares
c.Spawner.server_token_scopes = [
    "shares!server",  # manage shares
    "servers!server",  # start/stop itself
    "users:activity!server",  # report activity (default permission)
]
```

This method is not preferable, because it means anyone with _access_ to the server also has access to the token to grant further sharing permissions,
which is not the case when using the oauth permissions above,
where each visiting user has their own permissions.

But it is more convenient for demonstration purposes, because we can write a Python notebook to use it, share-api.ipynb.

## Run the example

First, launch jupyterhub: `jupyterhub`.

Then login as the user `sharer`.

Run the first couple of cells of the notebook, until you get a `/hub/accept-share` URL.

Open a new private browser window, and paste this URL. When prompted, login with the username `shared-with`.

In the end, you should arrive at `sharer`'s server as the user `shared-with`.

After visiting as `shared-with`, you can proceed in the notebook as `sharer` and view who has permissions, revoke share codes, permissions, etc.
