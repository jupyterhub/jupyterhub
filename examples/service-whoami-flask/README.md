# Authenticating a flask service with JupyterHub

Uses `jupyterhub.services.HubAuth` to authenticate requests with the Hub in a [flask][] application.

## Run

1. Launch JupyterHub and the `whoami service` with

        jupyterhub --ip=127.0.0.1

2. Visit http://127.0.0.1:8000/services/whoami/ or http://127.0.0.1:8000/services/whoami-oauth/

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

This relies on the Hub starting the whoami service, via config (see [jupyterhub_config.py](./jupyterhub_config.py)).

A similar service could be run externally, by setting the JupyterHub service environment variables:

    JUPYTERHUB_API_TOKEN
    JUPYTERHUB_SERVICE_PREFIX


[flask]: http://flask.pocoo.org
