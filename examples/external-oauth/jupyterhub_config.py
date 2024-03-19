import os

# get the oauth client's API token.
# this could come from anywhere
api_token = os.getenv("JUPYTERHUB_API_TOKEN")
if not api_token:
    raise ValueError(
        "Make sure to `export JUPYTERHUB_API_TOKEN=$(openssl rand -hex 32)`"
    )

c = get_config()  # noqa
# tell JupyterHub to register the service as an external oauth client
c.JupyterHub.services = [
    {
        'name': 'external-oauth',
        'oauth_client_id': "service-oauth-client-test",
        'api_token': api_token,
        'oauth_redirect_uri': 'http://127.0.0.1:5555/oauth_callback',
    }
]

# Grant all JupyterHub users ability to access services
c.JupyterHub.load_roles = [
    {
        'name': 'user',
        'description': 'Allow all users to access all services',
        'scopes': ['access:services', 'self'],
    }
]

# Boilerplate to make sure the example runs - this is not relevant
# to external oauth services.

# Allow authentication with any username and any password
from jupyterhub.auth import DummyAuthenticator

c.JupyterHub.authenticator_class = DummyAuthenticator

# Optionally set a global password that all users must use
# c.DummyAuthenticator.password = "your_password"

# only listen on localhost for testing.
c.JupyterHub.bind_url = 'http://127.0.0.1:8000'
