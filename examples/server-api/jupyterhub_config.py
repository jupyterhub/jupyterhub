# create a role with permissions to:
# 1. start/stop servers, and
# 2. access the server API

c = get_config()  # noqa

c.JupyterHub.load_roles = [
    {
        "name": "launcher",
        "scopes": [
            "servers",  # manage servers
            "access:servers",  # access servers themselves
        ],
        # assign role to our 'launcher' service
        "services": ["launcher"],
    }
]


# persist token to a file, to share it with the launch-server.py script
import pathlib
import secrets

here = pathlib.Path(__file__).parent
token_file = here.joinpath("service-token")
if token_file.exists():
    with token_file.open("r") as f:
        token = f.read()
else:
    token = secrets.token_hex(16)
    with token_file.open("w") as f:
        f.write(token)

# define our service
c.JupyterHub.services = [
    {
        "name": "launcher",
        "api_token": token,
    }
]

# ensure spawn requests return immediately,
# rather than waiting up to 10 seconds for spawn to complete
# this ensures that we use the progress API

c.JupyterHub.tornado_settings = {"slow_spawn_timeout": 0}

# create our test-user
c.Authenticator.allowed_users = {
    'test-user',
}


# testing boilerplate: fake auth/spawner, localhost. Don't use this for real!
c.JupyterHub.authenticator_class = 'dummy'
c.JupyterHub.spawner_class = 'simple'
c.JupyterHub.ip = '127.0.0.1'
