# Authenticating a flask service with JupyterHub

Uses `jupyterhub.services.HubOAuth` to authenticate requests with the Hub in a [flask][] application.

## Run

1.  Launch JupyterHub and the `whoami service` with

        jupyterhub --ip=127.0.0.1

2.  Visit http://127.0.0.1:8000/services/whoami/

After logging in with your local-system credentials, you should see a JSON dump of your user info:

```json
{
  "admin": false,
  "groups": [],
  "kind": "user",
  "name": "queequeg",
  "scopes": [
    "access:services!service=whoami",
    "read:users:groups!user=queequeg",
    "read:users:name!user=queequeg"
  ],
  "session_id": "a32e59cdd7b445759c58c48e47394a38"
}
```

This relies on the Hub starting the whoami service, via config (see [jupyterhub_config.py](./jupyterhub_config.py)). For ordinary users to access this service, they need to be given the appropriate scope (again, see [jupyterhub_config.py](./jupyterhub_config.py)).

A similar service could be run externally, by setting the JupyterHub service environment variables:

    JUPYTERHUB_API_TOKEN
    JUPYTERHUB_SERVICE_PREFIX

[flask]: http://flask.pocoo.org
