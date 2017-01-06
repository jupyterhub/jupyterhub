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

hub_ip = '127.0.0.1'
hub_api_port = 8081
service_name = 'shared-notebook'
group_name = 'shared'
service_port = 9999

# start the notebook server as a service
c.JupyterHub.services = [
    {
        'name': service_name,
        'url': 'http://127.0.0.1:{}'.format(service_port),
        'command': [
            'jupyterhub-singleuser',
            '--cookie-name=jupyterhub-services',
            '--port={}'.format(service_port),
            '--group={}'.format(group_name),
            '--base-url=/services/{}'.format(service_name),
            '--hub-prefix=/hub/',
            '--hub-api-url=http://{}:{}/hub/api'.format(hub_ip, hub_api_port),
        ]
    }
]