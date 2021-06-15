# Authenticating a service with JupyterHub

Uses `jupyterhub.services.HubAuthenticated` to authenticate requests with the Hub.

There is an implementation each of api-token-based `HubAuthenticated` and OAuth-based `HubOAuthenticated`.

## Run

1.  Launch JupyterHub and the `whoami` services with

        jupyterhub --ip=127.0.0.1

2.  Visit http://127.0.0.1:8000/services/whoami-oauth

After logging in with your local-system credentials, you should see a JSON dump of your user info:

```json
{
  "admin": false,
  "last_activity": "2016-05-27T14:05:18.016372",
  "name": "queequeg",
  "pending": null,
  "server": "/user/queequeg"
}
```

The `whoami-api` service powered by the base `HubAuthenticated` class only supports token-authenticated API requests,
not browser visits, because it does not implement OAuth. Visit it by requesting an api token from the tokens page,
and making a direct request:

```bash
$ curl -H "Authorization: token 8630bbd8ef064c48b22c7f122f0cd8ad" http://127.0.0.1:8000/services/whoami-api/ | jq .
{
  "admin": false,
  "created": "2021-05-21T09:47:41.299400Z",
  "groups": [],
  "kind": "user",
  "last_activity": "2021-05-21T09:49:08.290745Z",
  "name": "test",
  "pending": null,
  "roles": [
    "user"
  ],
  "scopes": [
    "access:services",
    "access:servers!user=test",
    "read:users!user=test",
    "read:users:activity!user=test",
    "read:users:groups!user=test",
    "read:users:name!user=test",
    "read:servers!user=test",
    "read:tokens!user=test",
    "users!user=test",
    "users:activity!user=test",
    "users:groups!user=test",
    "users:name!user=test",
    "servers!user=test",
    "tokens!user=test"
  ],
  "server": null
}
```

This relies on the Hub starting the whoami services, via config (see [jupyterhub_config.py](./jupyterhub_config.py)).

To govern access to the services, create **roles** with the scope `access:services!service=$service-name`,
and assign users to the scope.

The jupyterhub_config.py grants access for all users to all services via the default 'user' role, with:

```python
c.JupyterHub.load_roles = [
    {
        "name": "user",
        # grant all users access to all services
        "scopes": ["access:services", "self"],
    }
]
```

A similar service could be run externally, by setting the JupyterHub service environment variables:

    JUPYTERHUB_API_TOKEN
    JUPYTERHUB_SERVICE_PREFIX
    JUPYTERHUB_OAUTH_SCOPES
    JUPYTERHUB_CLIENT_ID # for whoami-oauth only

or instantiating and configuring a HubAuth object yourself, and attaching it as `self.hub_auth` in your HubAuthenticated handlers.
