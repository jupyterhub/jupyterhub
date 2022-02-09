import sys

c.JupyterHub.services = [
    {
        'name': 'whoami-api',
        'url': 'http://127.0.0.1:10101',
        'command': [sys.executable, './whoami.py'],
    },
    {
        'name': 'whoami-oauth',
        'url': 'http://127.0.0.1:10102',
        'command': [sys.executable, './whoami-oauth.py'],
        # the default oauth roles is minimal,
        # only requesting access to the service,
        # and identification by name,
        # nothing more.
        # Specifying 'oauth_roles' as a list of role names
        # allows requesting more information about users,
        # or the ability to take actions on users' behalf, as required.
        # The default 'token' role has the full permissions of its owner:
        # 'oauth_roles': ['token'],
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
