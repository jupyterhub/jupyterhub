c.JupyterHub.services = [
    {
        'name': 'whoami',
        'url': 'http://127.0.0.1:10101',
        'command': ['flask', 'run', '--port=10101'],
        'environment': {'FLASK_APP': 'whoami-flask.py'},
    },
    {
        'name': 'whoami-oauth',
        'url': 'http://127.0.0.1:10201',
        'command': ['flask', 'run', '--port=10201'],
        'environment': {'FLASK_APP': 'whoami-oauth.py'},
    },
]
