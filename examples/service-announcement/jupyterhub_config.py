import sys

# To run the announcement service managed by the hub, add this.

port = 9999
c.JupyterHub.services = [
    {
        'name': 'announcement',
        'url': f'http://127.0.0.1:{port}',
        'command': [
            sys.executable,
            "-m",
            "announcement",
            '--port',
            str(port),
        ],
    }
]

# The announcements need to get on the templates somehow, see page.html
# for an example of how to do this.

c.JupyterHub.template_paths = ["templates"]

c.Authenticator.allowed_users = {"announcer", "otheruser"}

# grant the 'announcer' permission to access the announcement service
c.JupyterHub.load_roles = [
    {
        "name": "announcers",
        "users": ["announcer"],
        "scopes": ["access:services!service=announcement"],
    }
]

# dummy spawner and authenticator for testing, don't actually use these!
c.JupyterHub.authenticator_class = 'dummy'
c.JupyterHub.spawner_class = 'simple'
c.JupyterHub.ip = '127.0.0.1'  # let's just run on localhost while dummy auth is enabled
