"""sample jupyterhub config file for testing

configures jupyterhub with dummyauthenticator and simplespawner
to enable testing without administrative privileges.
"""

c = get_config()  # noqa
c.Application.log_level = 'DEBUG'

import os

from oauthenticator.azuread import AzureAdOAuthenticator

c.JupyterHub.authenticator_class = AzureAdOAuthenticator

c.AzureAdOAuthenticator.client_id = os.getenv("AAD_CLIENT_ID")
c.AzureAdOAuthenticator.client_secret = os.getenv("AAD_CLIENT_SECRET")
c.AzureAdOAuthenticator.oauth_callback_url = os.getenv("AAD_CALLBACK_URL")
c.AzureAdOAuthenticator.tenant_id = os.getenv("AAD_TENANT_ID")
c.AzureAdOAuthenticator.username_claim = "email"
c.AzureAdOAuthenticator.authorize_url = os.getenv("AAD_AUTHORIZE_URL")
c.AzureAdOAuthenticator.token_url = os.getenv("AAD_TOKEN_URL")
c.Authenticator.manage_groups = True
c.Authenticator.refresh_pre_spawn = True

# Optionally set a global password that all users must use
# c.DummyAuthenticator.password = "your_password"

from jupyterhub.spawner import SimpleLocalProcessSpawner

c.JupyterHub.spawner_class = SimpleLocalProcessSpawner
