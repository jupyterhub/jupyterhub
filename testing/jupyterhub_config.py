from jupyterhub.auth import DummyAuthenticator

"""sample jupyterhub config file for testing

configures jupyterhub with dummyauthenticator and simplespawner
to enable testing without administrative privileges.
"""

c = get_config() # noqa
c.JupyterHub.authenticator_class = DummyAuthenticator

try:
    from jupyterhub.spawners import SimpleSpawner
except ImportError:
    print("simplespawner not available. Try: `pip install jupyterhub-simplespawner`")
else:
    c.JupyterHub.spawner_class = SimpleLocalProcessSpawner
