import os

# get the oauth client's API token.
# this could come from anywhere
api_token = os.getenv("JUPYTERHUB_API_TOKEN")
if not api_token:
    raise ValueError(
        "Make sure to `export JUPYTERHUB_API_TOKEN=$(openssl rand -hex 32)`"
    )

# tell JupyterHub to register the service as an external oauth client

c.JupyterHub.services = [
    {
        'name': 'external-oauth',
        'oauth_client_id': "whoami-oauth-client-test",
        'api_token': api_token,
        'oauth_redirect_uri': 'http://127.0.0.1:5555/oauth_callback',
    }
]
