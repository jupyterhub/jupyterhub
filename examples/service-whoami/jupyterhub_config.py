import sys

c = get_config()  # noqa

c.JupyterHub.services = [
    {
        'name': 'whoami-api',
        'url': 'http://127.0.0.1:10101',
        'command': [sys.executable, './whoami.py'],
        'display': False,
    },
    {
        'name': 'whoami-oauth',
        'url': 'http://127.0.0.1:10102',
        'command': [sys.executable, './whoami-oauth.py'],
        # the default oauth roles is minimal,
        # only requesting access to the service,
        # and identification by name,
        # nothing more.
        # Specifying 'oauth_client_allowed_scopes' as a list of scopes
        # allows requesting more information about users,
        # or the ability to take actions on users' behalf, as required.
        # the 'inherit' scope means the full permissions of the owner
        # 'oauth_client_allowed_scopes': ['inherit'],
    },
]

c.JupyterHub.load_roles = [
    {
        "name": "user",
        # grant all users access to all services
        "scopes": ["access:services", "self"],
    }
]

# dummy spawner and authenticator for testing, don't actually use these!
c.JupyterHub.authenticator_class = 'dummy'
c.JupyterHub.spawner_class = 'simple'
c.JupyterHub.ip = '127.0.0.1'  # let's just run on localhost while dummy auth is enabled
# default to home page, since we don't want to start servers for this demo
c.JupyterHub.default_url = "/hub/home"
