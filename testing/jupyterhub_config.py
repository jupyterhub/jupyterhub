from jupyterhub.auth import DummyAuthenticator

"""sample jupyterhub config file for testing

configures jupyterhub with dummyauthenticator and simplespawner
to enable testing without administrative privileges.
"""

c = get_config() # noqa
c.JupyterHub.authenticator_class = DummyAuthenticator

# Optionally set a global password that all users must use
# c.DummyAuthenticator.password = "your_password"

try:
    from simplespawner import SimpleLocalProcessSpawner
except ImportError:
    print("simplespawner not available. Try: `pip install jupyterhub-simplespawner`")
else:
    c.JupyterHub.spawner_class = SimpleLocalProcessSpawner
