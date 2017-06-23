# our user list
c.Authenticator.whitelist = [
    'minrk',
    'ellisonbg',
    'willingc',
]

# ellisonbg and willingc have access to a shared server:

c.JupyterHub.load_groups = {
    'shared': [
        'ellisonbg',
        'willingc',
    ]
}

# start the notebook server as a service
c.JupyterHub.services = [
    {
        'name': 'shared-notebook',
        'url': 'http://127.0.0.1:9999',
        'api_token': 'super-secret',
    }
]