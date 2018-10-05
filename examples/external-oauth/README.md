# Using JupyterHub as an OAuth provider

JupyterHub 0.9 introduces the ability to use JupyterHub as an OAuth provider
for external services that may not be otherwise integrated with JupyterHub.
The main feature this enables is using JupyterHub like a 'regular' OAuth 2
provider for services running anywhere.

There are two examples here. `whoami-oauth` (in the service-whoami directory) uses `jupyterhub.services.HubOAuthenticated`
to authenticate requests with the Hub for a service run on its own host.
This is an implementation of OAuth 2.0 provided by the jupyterhub package,
which configures all of the necessary URLs from environment variables.

The second is `whoami-oauth-basic`, which implements the full OAuth process
without any inheritance, so it can be used as a reference for OAuth
implementations in other web servers or languages.

## Run the example

1. generate an API token:

        export JUPYTERHUB_API_TOKEN=$(openssl rand -hex 32)

2. launch a version of the the whoami service.
   For `whoami-oauth`:

        bash launch-service.sh &

    or for `whoami-oauth-basic`:

        bash launch-service-basic.sh &

3. Launch JupyterHub:

        jupyterhub

4. Visit http://127.0.0.1:5555/

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


The essential pieces for using JupyterHub as an OAuth provider are:

1. registering your service with jupyterhub:

    ```python
    c.JupyterHub.services = [
        {
            # the name of your service
            # should be simple and unique.
            # mostly used to identify your service in logging
            "name": "my-service",
            # the oauth client id of your service
            # must be unique but isn't private
            # can be randomly generated or hand-written
            "oauth_client_id": "abc123",
            # the API token and client secret of the service
            # should be generated securely,
            # e.g. via `openssl rand -hex 32`
            "api_token": "abc123...",
            # the redirect target for jupyterhub to send users
            # after successful authentication
            "oauth_redirect_uri": "https://service-host/oauth_callback"
        }
    ]
    ```

2. Telling your service how to authenticate with JupyterHub.

The relevant OAuth URLs and keys for using JupyterHub as an OAuth provider are:

1. the client_id, used in oauth requests
2. the api token registered with jupyterhub is the client_secret for oauth requests
3. oauth url of the Hub, which is "/hub/api/oauth2/authorize", e.g. `https://myhub.horse/hub/api/oauth2/authorize`
4. a redirect handler to receive the authenticated response
   (at `oauth_redirect_uri` registered in jupyterhub config)
5. the token URL for completing the oauth process is "/hub/api/oauth2/token",
   e.g. `https://myhub.horse/hub/api/oauth2/token`.
   The reply is JSON and the token is in the field `access_token`.
6. Users can be identified by oauth token by making a request to `/hub/api/user`
   with the new token in the `Authorization` header.
