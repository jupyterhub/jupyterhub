# User-initiated sharing

This example contains a jupyterhub configuration and sample notebook demonstrating user-initiated sharing from within a JupyterLab session.

What _admins_ need to do is enable sharing:

```python
c.JupyterHub.load_roles = [
    {
        "name": "user",
        "scopes": ["self", "shares!user"],
    }
]
```

And to make it more convenient, grant this permission tot he default token used,
so sharing actions can be taken from JupyterLab javascript:

```python
# OAuth token should have sharing permissions,
# so JupyterLab javascript can manage shares
c.Spawner.oauth_client_allowed_scopes = ["access:servers!server", "shares!server"]
```

(users can workaround this by issuing their own tokens from the tokens API).

Finally, there is a notebook containing a few javascript snippets which will use the JupyterLab configuration to make API requests to JupyterHub in order to grant acc

This workflow _should_ be handled by a proper JupyterLab extension,
but this notebook of javascript snippets serves as a proof of concept for what is required to build such an extension.

## Run the example

First, launch jupyterhub: `jupyterhub`.

Then login as the user `sharer`.

Run the first couple of cells of the notebook, until you get a `/hub/accept-share` URL.

Open a new private browser window, and paste this URL. When prompted, login with the username `shared-with`.

In the end, you should arrive at `sharer`'s server as the user `shared-with`.

After visiting as `shared-with`, you can proceed in the notebook as `sharer` and view who has permissions, revoke share codes, permissions, etc.
