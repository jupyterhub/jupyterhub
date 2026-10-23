"""
Demonstrate using oauth2-proxy to protect an upstream service,
using JupyterHub OIDC.

configures jupyterhub with dummyauthenticator and simplespawner
to enable testing without administrative privileges.
"""

import os

c = get_config()  # noqa

# need public_url set for OIDC Issuer to be consistent
c.JupyterHub.public_url = 'http://127.0.0.1:8000'

# users have access to services
c.JupyterHub.extra_user_scopes = {"access:services"}
# server token also has access to services
c.Spawner.server_token_scopes = ["access:services"]

c.JupyterHub.services = [
    # register oauth2-proxy as a service
    {
        "name": "oauth2-proxy",
        "api_token": "067480423daa83eb9d315cedeef75bbe58798c6",
        "oauth_redirect_uri": "http://127.0.0.1:4180/oauth2/callback",
        "command": [
            "oauth2-proxy",
            "--config",
            "./oauth2-proxy.cfg",
            "--alpha-config",
            "./oauth2-proxy.yaml",
        ],
    },
    # echo service is a managed service for easier process management,
    # it does not use the JupyterHub API at all
    {
        "name": "echo",
        "command": [
            "python3",
            "echo.py",
        ],
    },
]

## Demo boilerplate

# only listen on localhost for testing
c.JupyterHub.bind_url = 'http://127.0.0.1:8000'

# make sure admin UI is available and any user can login
c.Authenticator.admin_users = {"admin"}
c.Authenticator.allow_all = True
c.JupyterHub.authenticator_class = "dummy"

# Optionally set a global password that all users must use
# c.DummyAuthenticator.password = "your_password"

c.JupyterHub.spawner_class = "simple"

# start users in example directory
c.SimpleLocalProcessSpawner.home_dir_template = os.getcwd()
c.JupyterHub.cleanup_servers = False
