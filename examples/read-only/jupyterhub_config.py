c = get_config()  # noqa

# define custom scopes so they can be assigned to users
# these could be

c.JupyterHub.custom_scopes = {
    "custom:jupyter_server:read:*": {
        "description": "read-only access to your server",
    },
    "custom:jupyter_server:write:*": {
        "description": "access to modify files on your server. Does not include execution.",
        "subscopes": ["custom:jupyter_server:read:*"],
    },
    "custom:jupyter_server:execute:*": {
        "description": "Execute permissions on servers.",
        "subscopes": [
            "custom:jupyter_server:write:*",
            "custom:jupyter_server:read:*",
        ],
    },
}

c.JupyterHub.load_roles = [
    # grant specific users read-only access to all servers
    {
        "name": "read-only-all",
        "scopes": [
            "access:servers",
            "custom:jupyter_server:read:*",
        ],
        "groups": ["read-only"],
    },
    {
        "name": "read-only-read-only-percy",
        "scopes": [
            "access:servers!user=percy",
            "custom:jupyter_server:read:*!user=percy",
        ],
        "users": ["vex"],
    },
    {
        "name": "admin-ui",
        "scopes": [
            "admin-ui",
            "list:users",
            "admin:servers",
        ],
        "users": ["admin"],
    },
    {
        "name": "full-access",
        "scopes": [
            "access:servers",
            "custom:jupyter_server:execute:*",
        ],
        "users": ["minrk"],
    },
    # all users have full access to their own servers
    {
        "name": "user",
        "scopes": [
            "custom:jupyter_server:execute:*!user",
            "custom:jupyter_server:read:*!user",
            "self",
        ],
    },
]

# servers request access to themselves

c.Spawner.oauth_client_allowed_scopes = [
    "access:servers!server",
    "custom:jupyter_server:read:*!server",
    "custom:jupyter_server:execute:*!server",
]

# enable the jupyter-server extension
c.Spawner.environment = {
    "JUPYTERHUB_SINGLEUSER_EXTENSION": "1",
}

from pathlib import Path

here = Path(__file__).parent.resolve()

# load the server config that enables granular permissions
c.Spawner.args = [
    f"--config={here}/jupyter_server_config.py",
]


# example boilerplate: dummy auth/spawner
c.JupyterHub.authenticator_class = 'dummy'
c.JupyterHub.spawner_class = 'simple'
c.JupyterHub.ip = '127.0.0.1'
