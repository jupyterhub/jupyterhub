# run cull-idle as a service
c.JupyterHub.services = [
    {
        'name': 'cull-idle',
        'admin': True,
        'command': 'python3 cull_idle_servers.py --timeout=3600'.split(),
    }
]
