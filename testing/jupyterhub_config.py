"""sample jupyterhub config file for testing

configures jupyterhub with dummyauthenticator and simplespawner
to enable testing without administrative privileges.
"""

c = get_config() # noqa

try:
    from dummyauthenticator import DummyAuthenticator
except ImportError:
    print("dummyauthenticator not available. Try: `pip install jupyterhub-dummyauthenticator`")
else:
    c.JupyterHub.authenticator_class = DummyAuthenticator

try:
    from simplespawner import SimpleLocalProcessSpawner
except ImportError:
    print("simplespawner not available. Try: `pip install jupyterhub-simplespawner`")
else:
    c.JupyterHub.spawner_class = SimpleLocalProcessSpawner
