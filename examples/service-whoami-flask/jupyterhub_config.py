c = get_config()  # noqa

c.JupyterHub.services = [
    {
        'name': 'whoami',
        'url': 'http://127.0.0.1:10101',
        'command': ['flask', 'run', '--port=10101'],
        'environment': {'FLASK_APP': 'whoami-flask.py'},
    },
]
c.JupyterHub.load_roles = [
    {
        'name': 'user',
        'scopes': [
            'access:services!service=whoami',  # access this service
            'self',  # and all of the standard things for a user
        ],
    }
]

# dummy auth and simple spawner for testing
# any username and password will work
c.JupyterHub.spawner_class = 'simple'
c.JupyterHub.authenticator_class = 'dummy'

# listen only on localhost while testing with wide-open auth
c.JupyterHub.ip = '127.0.0.1'
