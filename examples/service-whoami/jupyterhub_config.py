import sys

c.JupyterHub.services = [
    {
        'name': 'whoami',
        'url': 'http://127.0.0.1:10101',
        'command': [sys.executable, './whoami.py'],
    },
    {
        'name': 'whoami-oauth',
        'url': 'http://127.0.0.1:10102',
        'command': [sys.executable, './whoami-oauth.py'],
    },
]
