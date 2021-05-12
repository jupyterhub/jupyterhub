# our user list
c.Authenticator.allowed_users = ['minrk', 'ellisonbg', 'willingc']

# ellisonbg and willingc have access to a shared server:

c.JupyterHub.load_groups = {'shared-notebook-grp': ['ellisonbg', 'willingc']}

c.JupyterHub.load_roles = [
    {
        "name": "shared-notebook",
        "groups": ["shared-notebook-grp"],
        "scopes": ["access:services!service=shared-notebook"],
    },
    # by default, the user role has access to all services
    # we want to limit that, so give users only access to 'self'
    {
        "name": "user",
        "scopes": ["self"],
    },
]

# start the notebook server as a service
c.JupyterHub.services = [
    {
        'name': 'shared-notebook',
        'url': 'http://127.0.0.1:9999',
        'api_token': 'c3a29e5d386fd7c9aa1e8fe9d41c282ec8b',
    }
]

# dummy spawner and authenticator for testing, don't actually use these!
c.JupyterHub.authenticator_class = 'dummy'
c.JupyterHub.spawner_class = 'simple'
