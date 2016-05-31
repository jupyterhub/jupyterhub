# Authenticating a service with JupyterHub

Uses `jupyterhub.services.HubAuthenticated` to authenticate requests with the Hub.

## Run

1. Launch JupyterHub and the `whoami service` with `source launch.sh`.
2. Visit http://127.0.0.1:8000/hub/whoami

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
