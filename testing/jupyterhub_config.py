from jupyterhub.auth import DummyAuthenticator

"""sample jupyterhub config file for testing

configures jupyterhub with dummyauthenticator and simplespawner
to enable testing without administrative privileges.
"""

c = get_config() # noqa
c.JupyterHub.authenticator_class = DummyAuthenticator

from jupyterhub.spawners import SimpleSpawner
c.JupyterHub.spawner_class = SimpleSpawner

