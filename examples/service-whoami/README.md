# Authenticating a service with JupyterHub

Uses `jupyterhub.services.HubAuthenticated` to authenticate requests with the Hub.

There is an implementation each of api-token-based `HubAuthenticated` and OAuth-based `HubOAuthenticated`.

## Run

1.  Launch JupyterHub and the `whoami` services with

        jupyterhub

2.  Visit http://127.0.0.1:8000/services/whoami-oauth

After logging in with any username and password, you should see a JSON dump of your user info:

```json
{
  "admin": false,
  "groups": [],
  "kind": "user",
  "name": "queequeg",
  "scopes": ["access:services!service=whoami-oauth"],
  "session_id": "5a2164273a7346728873bcc2e3c26415"
}
```

What is contained in the model will depend on the permissions
requested in the `oauth_client_allowed_scopes` configuration of the service `whoami-oauth` service.
The default is the minimum required for identification and access to the service,
which will provide the username and current scopes.

The `whoami-api` service powered by the base `HubAuthenticated` class only supports token-authenticated API requests,
not browser visits, because it does not implement OAuth. Visit it by requesting an api token from the tokens page (`/hub/token`),
and making a direct request:

```bash
token="d584cbc5bba2430fb153aadb305029b4"
curl -H "Authorization: token $token" http://127.0.0.1:8000/services/whoami-api/ | jq .
```

```json
{
  "admin": false,
  "created": "2021-12-20T09:49:37.258427Z",
  "groups": [],
  "kind": "user",
  "last_activity": "2021-12-20T10:07:31.298056Z",
  "name": "queequeg",
  "pending": null,
  "roles": ["user"],
  "scopes": [
    "access:servers!user=queequeg",
    "access:services",
    "delete:servers!user=queequeg",
    "read:servers!user=queequeg",
    "read:tokens!user=queequeg",
    "read:users!user=queequeg",
    "read:users:activity!user=queequeg",
    "read:users:groups!user=queequeg",
    "read:users:name!user=queequeg",
    "servers!user=queequeg",
    "tokens!user=queequeg",
    "users:activity!user=queequeg"
  ],
  "server": null,
  "servers": {},
  "session_id": null
}
```

The above is a more complete user model than the `whoami-oauth` example, because
the token was issued with the default `token` role,
which has the `inherit` metascope,
meaning the token has access to everything the tokens owner has access to.

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
