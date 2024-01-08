c = get_config()  # noqa


c.JupyterHub.authenticator_class = 'dummy'
c.JupyterHub.spawner_class = 'simple'

c.Authenticator.allowed_users = {"sharer", "shared-with"}

# put the current directory on sys.path for shareextension.py
from pathlib import Path

here = Path(__file__).parent.absolute()
c.Spawner.notebook_dir = str(here)

# users need sharing permissions for their own servers
c.JupyterHub.load_roles = [
    {
        "name": "user",
        "scopes": ["self", "shares!user"],
    }
]

# OAuth token should have sharing permissions,
# so JupyterLab javascript can manage shares
c.Spawner.oauth_client_allowed_scopes = ["access:servers!server", "shares!server"]
