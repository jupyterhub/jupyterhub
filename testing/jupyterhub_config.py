"""sample jupyterhub config file for testing

configures jupyterhub with dummyauthenticator and simplespawner
to enable testing without administrative privileges.
"""

c = get_config()  # noqa

c.JupyterHub.authenticator_class = "dummy"

# Optionally set a global password that all users must use
# c.DummyAuthenticator.password = "your_password"

c.JupyterHub.spawner_class = "simple"

# only listen on localhost for testing
c.JupyterHub.bind_url = 'http://127.0.0.1:8000'

# don't cache static files
c.JupyterHub.tornado_settings = {
    "no_cache_static": True,
    "slow_spawn_timeout": 0,
}

c.JupyterHub.allow_named_servers = True
c.JupyterHub.default_url = "/hub/home"

# make sure admin UI is available and any user can login
c.Authenticator.admin_users = {"admin"}
c.Authenticator.allow_all = True
