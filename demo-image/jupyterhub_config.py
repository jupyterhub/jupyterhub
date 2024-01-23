# Configuration file for jupyterhub-demo

c = get_config()  # noqa

# Use DummyAuthenticator and SimpleSpawner
c.JupyterHub.spawner_class = "simple"
c.JupyterHub.authenticator_class = "dummy"
